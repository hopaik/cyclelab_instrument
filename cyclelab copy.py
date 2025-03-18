import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from Levenshtein import distance as levenshtein_distance
import time
import threading
import streamlit.components.v1 as components
from datetime import datetime
from pytz import all_timezones, timezone


st.set_page_config(layout="wide")

# DB 연결 정보
config_maindb = {
    "user": "hopaik", 
    "password": "Coinupbit3261$",
    "host": "hopaik.synology.me",
    "database": "practice_routine"
}

# SQLAlchemy 엔진 생성
engine_mainDB = create_engine(
    f"mysql+pymysql://{config_maindb['user']}:{config_maindb['password']}@{config_maindb['host']}/{config_maindb['database']}",
    pool_size=10
)

# 세션 상태 초기화
if 'formState_addToDo' not in st.session_state:
    st.session_state.formState_addToDo = 'close'
if 'show_title_form' not in st.session_state:
    st.session_state.show_title_form = False
if 'show_selected_row' not in st.session_state:
    st.session_state.show_selected_row = False
if 'formState_selected_row' not in st.session_state:
    st.session_state.formState_selected_row = 'close'
if 'formState_editToDo' not in st.session_state:
    st.session_state.formState_editToDo = 'close'





options_genre = ['장르1', '장르2', '장르3']
options_style1 = ['스타일1', '스타일2', '스타일3']
options_style2 = ['스타일4', '스타일5', '스타일6']
options_key1 = ['키1', '키2', '키3']
options_key2 = ['키4', '키5', '키6']
options_completion_level = ['Level_0', 'Level_1', 'Level_2', 'Level_3']



def get_today_local():
    # JavaScript로 클라이언트의 오늘 날짜를 가져오기
    js_code = """
    <script>
        const localDate = new Date().toISOString().split('T')[0]; // YYYY-MM-DD 형식
        document.getElementById("local_date").innerHTML = localDate;
    </script>
    <div id="local_date" style="display:none;"></div>
    """
    components.html(js_code, height=0)
    
    # Streamlit은 JS 값을 직접 못 읽으므로, 세션 상태로 관리하거나 수동 입력 대체
    if 'today_local' not in st.session_state:
        # 초기값 설정 (임시로 서버 날짜 사용, JS 값은 별도 처리 필요)
        st.session_state['today_local'] = pd.to_datetime('today').date()
    return st.session_state['today_local']





def convertTo_localDate(timestamp_utc):
    try:
        timestamp_numeric = float(timestamp_utc) if timestamp_utc is not None else None
        if timestamp_numeric is None:
            return None
        return pd.to_datetime(timestamp_numeric, unit='s').tz_localize('UTC').tz_convert(client_timezone).date()
    except (ValueError, TypeError):
        return None  

def convertTo_timestamp_utc(date_local):
    try:
        if date_local is None:
            return None
        date_str = str(date_local)
        # pd.to_datetime으로 파싱, 기본적으로 날짜만 있는 경우 00:00:00으로 설정
        dt = pd.to_datetime(date_str)
        # client_timezone으로 로컬라이즈 후 UTC로 변환, 타임스탬프 반환
        return dt.tz_localize(client_timezone).tz_convert('UTC').timestamp()
    except (ValueError, TypeError):
        return None  



# 데이터 로드 (테이블이 없으면 생성)
def load_from_db():
    def get_dataframe_from_db(table_name, columns, create_table_sql):
        try:
            return pd.read_sql(f'SELECT * FROM {table_name}', con=engine_mainDB)
        except Exception as e:
            with engine_mainDB.connect() as connection:
                connection.execute(text(create_table_sql))
                connection.commit()
            return pd.DataFrame(columns=columns)
    df_todo = get_dataframe_from_db(
        'todo',
        ['id', 'title', 'start_date_local', 'last_completion_date_local', 'repeat_cycle', 'continuous_count_perCycle', 'due_date_local', 'd_day_local', 'days_elapsed', 'accumulated_min', 'completion_count', 'status', 'completion_level'],
        """
        CREATE TABLE IF NOT EXISTS todo (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            start_timestamp_utc INT,
            last_completion_timestamp_utc INT,
            due_timestamp_utc INT,
            start_date_local DATE,
            last_completion_date_local DATE,
            due_date_local DATE,
            d_day_local INT, 
            days_elapsed INT,
            repeat_cycle INT,
            continuous_count_perCycle INT,
            accumulated_min INT,
            completion_count INT,
            status VARCHAR(255),
            completion_level VARCHAR(255)
        )
        """
    )
    return df_todo


df_todo = load_from_db()
client_timezone = "Asia/Seoul"
today_local = get_today_local()

# def update_db_todo(df_new_todo):
#     global df_todo
#     import numpy as np  # numpy 임포트 추가
#     if df_new_todo.empty:
#         return False
#     # df_new_todo의 None을 np.nan으로 변환
#     df_new_todo = df_new_todo.replace({None: np.nan}).infer_objects(copy=False)
#     if df_todo.empty:
#         df_todo = df_new_todo
#     elif df_new_todo["id"].iloc[0] in df_todo["id"].values:
#         df_todo.loc[df_todo["id"] == df_new_todo["id"].iloc[0]] = df_new_todo
#     else:
#         df_todo = pd.concat([df_todo, df_new_todo], ignore_index=True)

#     try:
#         df_todo.to_sql('todo', con=engine_mainDB, if_exists='replace', index=False)
#         return True
#     except Exception as e:
#         st.error('데이터 저장 중 오류가 발생했습니다.')
#         return False
    

def update_db_todo(df_new_todo):
    global df_todo
    import numpy as np  # numpy 임포트 추가
    if df_new_todo.empty:
        return False
    # None을 np.nan으로 변환, 다운캐스팅 경고 방지
    pd.set_option('future.no_silent_downcasting', True)  # 미래 동작 수용
    df_new_todo = df_new_todo.replace({None: np.nan})
    if df_todo.empty:
        df_todo = df_new_todo
    elif df_new_todo["id"].iloc[0] in df_todo["id"].values:
        df_todo.loc[df_todo["id"] == df_new_todo["id"].iloc[0]] = df_new_todo
    else:
        df_todo = pd.concat([df_todo, df_new_todo], ignore_index=True)

    try:
        df_todo.to_sql('todo', con=engine_mainDB, if_exists='replace', index=False)
        return True
    except Exception as e:
        st.error('데이터 저장 중 오류가 발생했습니다.')
        return False
    





def add_todo():
    global df_todo
    global client_timezone
    global today_local

    # 모든 시간대 지역 표시, 선택
    client_timezone = st.selectbox("당신의 시간대", options=all_timezones, index=all_timezones.index("Asia/Seoul"), key="client_timezone", help="시간대를 선택하세요")
    if st.session_state.formState_addToDo == 'open':
        col2 = st.columns(1)
        with col2[0]:
            title_input = st.text_input('곡명', value="", key='title_input', help='곡명을 입력하세요')
        col3 = st.columns(2)
        with col3[0]:
            repeat_cycle_input = int(st.number_input('반복주기 (일)', min_value=1, value=1, key='repeat_cycle_input', help='반복주기(일)를 입력하세요', step=1))
        with col3[1]:
            continuous_count_perCycle = int(st.number_input('연속일 횟수', min_value=1, value=1, key='continuous_count_perCycle', help='반복주기마다 수행해야 할 연속일 횟수를 입력하세요', step=1))
        col4 = st.columns(2)
        with col4[0]:
            # 클라이언트 로컬 날짜로 초기값 설정
            start_date_input = st.date_input('시작일 (예정일)', value=today_local, min_value=today_local, key='start_date_input', help='시작일을 선택하세요')
        with col4[1]:
            completion_level = st.selectbox('완료 레벨', options=options_completion_level, index=0, key='completion_level', help='완료 레벨을 선택하세요')
        col5 = st.columns(2)
        with col5[0]:
            status_input = st.selectbox('상태', options=['미처리', '연습중', '예정'], index=0, key='status_input', help='상태를 선택하세요')
        col6 = st.columns(4)
        
        
        with col6[2]:
            if st.button('저장'):
                if title_input != "":
                    st.session_state.formState_addToDo = 'close'
                    st.session_state.show_title_form = False

                    if df_todo.empty:
                        new_id = 1
                    else:
                        new_id = df_todo['id'].max() + 1

                    # 클라이언트 로컬 시간대 기준으로 UTC 변환
                    start_timestamp_utc = convertTo_timestamp_utc(start_date_input)

                    # 예정일 계산
                    due_timestamp_utc = start_timestamp_utc

                    df_new_todo = pd.DataFrame({
                        'id': [new_id],
                        'title': [title_input],
                        'repeat_cycle': [repeat_cycle_input],
                        'continuous_count_perCycle': [continuous_count_perCycle],
                        'start_timestamp_utc': [start_timestamp_utc],
                        'last_completion_timestamp_utc': [None],
                        'due_timestamp_utc': [due_timestamp_utc],
                        'completion_level': [completion_level],
                        'status': [status_input],
                        'accumulated_min': [0],
                        'completion_count': [0],
                    })

                    update_db_todo(df_new_todo)
                    st.success('저장되었습니다')
                    st.rerun()
                else:
                    st.error('곡명을 입력하세요')

        with col6[3]:
            if st.button('취소'):
                st.session_state.formState_addToDo = 'close'
                st.session_state.show_title_form = False
                st.rerun()




@st.fragment
def show_stopWatch(todo_id):
    global df_todo
    
    if f'start_time_{todo_id}' not in st.session_state:
        st.session_state[f'start_time_{todo_id}'] = datetime.now()
    if f'running_{todo_id}' not in st.session_state:
        st.session_state[f'running_{todo_id}'] = False
    if f'elapsed_time_{todo_id}' not in st.session_state:
        st.session_state[f'elapsed_time_{todo_id}'] = 0
    if f'timer_last_updated_{todo_id}' not in st.session_state:
        st.session_state[f'timer_last_updated_{todo_id}'] = datetime.now()
    if f'settle_time_{todo_id}' not in st.session_state:
        st.session_state[f'settle_time_{todo_id}'] = False
    if f'completed_todo_{todo_id}' not in st.session_state:
        st.session_state[f'completed_todo_{todo_id}'] = False
    

    def update_elapsed_time():
        if st.session_state[f'running_{todo_id}']:
            current_time = datetime.now()
            time_diff = current_time - st.session_state[f'timer_last_updated_{todo_id}']
            st.session_state[f'elapsed_time_{todo_id}'] += time_diff.seconds
            st.session_state[f'timer_last_updated_{todo_id}'] = current_time

    def pause_timer():
        update_elapsed_time()
        st.session_state[f'running_{todo_id}'] = False

    def resume_timer():
        st.session_state[f'timer_last_updated_{todo_id}'] = datetime.now()
        st.session_state[f'running_{todo_id}'] = True

    def toggle_timer():
        if st.session_state[f'running_{todo_id}']:
            pause_timer()
        else:
            resume_timer()

    def reset_timer():
        st.session_state[f'elapsed_time_{todo_id}'] = 0
        st.session_state[f'running_{todo_id}'] = False
        st.session_state[f'timer_last_updated_{todo_id}'] = datetime.now()

    def settle_timer():
        pause_timer()
        # elapsed_time = st.session_state[f'elapsed_time_{todo_id}']
        # hours = elapsed_time // 3600
        # minutes = (elapsed_time % 3600) // 60
        # seconds = elapsed_time % 60
        # stopWatch = f"{hours:02}:{minutes:02}:{seconds:02}"
        st.session_state[f'settle_time_{todo_id}'] = True



    def show_completed_todo(todo_id):
        st.write("<div style='text-align: center;'>정산 완료!!! 🎉</div>", unsafe_allow_html=True)
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        time.sleep(3) #!!!광고 타임
        st.session_state[f'settle_time_{todo_id}'] = False
        st.session_state[f'completed_todo_{todo_id}'] = False
        reset_timer()
        st.rerun()
        


    def confirm_completed_todo(todo_id):
        global df_todo
        global today_local
        elapsed_sec = st.session_state[f'elapsed_time_{todo_id}']
        if elapsed_sec >= 60:
            last_completion_date_local = today_local
            repeat_cycle = int(df_todo.loc[df_todo['id'] == todo_id, 'repeat_cycle'].astype(int).values[0])
            due_date_local = last_completion_date_local + pd.Timedelta(days=repeat_cycle)
            last_completion_timestamp_utc = convertTo_timestamp_utc(last_completion_date_local)
            due_timestamp_utc = convertTo_timestamp_utc(due_date_local)

            elapsed_min = round(elapsed_sec / 60, 1)
            df_todo.loc[df_todo['id'] == todo_id, 'accumulated_min'] = df_todo.loc[df_todo['id'] == todo_id, 'accumulated_min'].astype(int) + elapsed_min
            df_todo.loc[df_todo['id'] == todo_id, 'completion_count'] += 1
            df_todo.loc[df_todo['id'] == todo_id, 'days_elapsed'] = 0
            df_todo.loc[df_todo['id'] == todo_id, 'last_completion_timestamp_utc'] = last_completion_timestamp_utc
            df_todo.loc[df_todo['id'] == todo_id, 'due_timestamp_utc'] = due_timestamp_utc
            st.session_state[f'settle_time_{todo_id}'] = False
            st.session_state[f'completed_todo_{todo_id}'] = True

            update_db_todo(df_todo)

        else:
            st.error('취소되었습니다. (최소 1분 이상이어야 정산 가능합니다.)')
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            time.sleep(3)
            st.session_state[f'settle_time_{todo_id}'] = False
        st.rerun()




    def show_adjust_and_confirm(todo_id):
        if st.button("위의 시간으로 정산 완료 할까요? (1분 미만 시 취소)", key=f"confirm_time_{todo_id}", use_container_width=True):
            confirm_completed_todo(todo_id)
        if st.button("+증가", key=f"increase_time_{todo_id}", use_container_width=True):
            st.session_state[f'elapsed_time_{todo_id}'] += 60  # 1분 증가
            st.rerun()
        if st.button("-감소", key=f"decrease_time_{todo_id}", use_container_width=True):
            if st.session_state[f'elapsed_time_{todo_id}'] >= 60:
                st.session_state[f'elapsed_time_{todo_id}'] -= 60  # 1분 감소
                st.rerun()


    def show_timer_display(todo_id):
        if st.session_state[f'running_{todo_id}']:
            update_elapsed_time()

        hours = st.session_state[f'elapsed_time_{todo_id}'] // 3600
        minutes = (st.session_state[f'elapsed_time_{todo_id}'] % 3600) // 60
        seconds = st.session_state[f'elapsed_time_{todo_id}'] % 60
        timer_display = f"{hours:02}:{minutes:02}:{seconds:02}"

    
        # 색상 로직 수정: running 상태를 먼저 체크
        if st.session_state[f'running_{todo_id}']:
            timer_color = "#FF0000"  # 진행 중이면 항상 빨강
        elif st.session_state[f'elapsed_time_{todo_id}'] == 0:
            timer_color = "#808080"  # 정지 상태이고 초기화면 회색
        else:
            timer_color = "#FF8C00"  # 정지 상태이고 시간이 쌓였으면 주황


        timer_html = f"""
        <div id="timer_{todo_id}" style="font-size: 48px; font-weight: bold; color: {timer_color}; text-align: center;">
            {timer_display}
        </div>
        <script>
            let seconds = {st.session_state[f'elapsed_time_{todo_id}']};
            let running = {'true' if st.session_state[f'running_{todo_id}'] else 'false'};
            let timerElement = document.getElementById('timer_{todo_id}');

            function updateTimerDisplay() {{
                if (running) {{
                    seconds++;
                    let h = Math.floor(seconds / 3600);
                    let m = Math.floor((seconds % 3600) / 60);
                    let s = seconds % 60;
                    timerElement.innerText = 
                        `${{h.toString().padStart(2, '0')}}:${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
                }}
            }}
            let intervalId = setInterval(updateTimerDisplay, 1000);
        </script>
        """
        components.html(timer_html, height=60)



    if st.session_state[f'completed_todo_{todo_id}']:
        show_completed_todo(todo_id)
    else:
        show_timer_display(todo_id)
        if not st.session_state[f'settle_time_{todo_id}']:
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.button("정지" if st.session_state[f'running_{todo_id}'] else "시작", 
                             key=f'toggle_button_{todo_id}', 
                             on_click=toggle_timer,
                             use_container_width=True)
                with col2:
                    st.button("리셋", 
                             key=f'reset_button_{todo_id}', 
                             on_click=reset_timer,
                             use_container_width=True)
                with col3:
                    st.button("정산", 
                             key=f'settle_button_{todo_id}', 
                             on_click=settle_timer,
                             use_container_width=True)
        else:
            show_adjust_and_confirm(todo_id)  #정산 버튼 클릭 시 호출 (시간조정, 확인)
    

    st.markdown("""
    <style>
    div[data-testid="column"] button {
        padding: 2.5px 1.25px;
        font-size: 12px;
        height: 20px;
        width: 25%;
        min-width: 10px;
    }
    </style>
    """, unsafe_allow_html=True)


def show_edit_form(selected_data):
    global df_todo
    global today_local
    todo_id = selected_data["id"].iloc[0]
    start_timestamp_utc = selected_data['start_timestamp_utc'].iloc[0]
    last_completion_timestamp_utc = selected_data['last_completion_timestamp_utc'].iloc[0]
    due_timestamp_utc = selected_data['due_timestamp_utc'].iloc[0]
    start_date_local = convertTo_localDate(start_timestamp_utc)
    last_completion_date_local = convertTo_localDate(last_completion_timestamp_utc)
    due_date_local = convertTo_localDate(due_timestamp_utc)

    with st.container(key=f'edit_form_{todo_id}'):
        title_input = st.text_input(label='곡명', value=selected_data['title'].iloc[0] if 'title' in selected_data else None, 
                      key=f'edit_title_{todo_id}', help='곡명을 입력하세요')
        
        repeat_cycle_input = st.number_input('반복주기 (일)', min_value=1, value=int(selected_data['repeat_cycle'].iloc[0]) if 'repeat_cycle' in selected_data else 1, key='edit_repeat_cycle_input', help='반복주기(일)를 입력하세요', step=1)
        
        continuous_count_perCycle_input = st.number_input('연속일 횟수', min_value=1, value=int(selected_data['continuous_count_perCycle'].iloc[0]) if 'continuous_count_perCycle' in selected_data else 1, key='edit_continuous_count_perCycle', help='반복주기마다 수행해야 할 연속일 횟수를 입력하세요', step=1)
        
        min_start_date = min(start_date_local, today_local)  # start_date_local이 today_local보다 이전일 수 있으므로
        
        start_date_input = st.date_input(label='시작일', value=start_date_local, 
                      min_value=min_start_date, key=f'edit_start_date_{todo_id}', disabled=True)
        
        last_completion_date_input = last_completion_date_local

        if pd.isna(last_completion_date_input):
            due_date_calculated = start_date_input
        else:
            due_date_calculated = last_completion_date_input + pd.Timedelta(days=repeat_cycle_input)


        due_date = due_date_local if due_date_local is not None else due_date_calculated

        due_date_input = st.date_input(label='다음 예정일', value=due_date, 
                      min_value=max(start_date_input, today_local), key=f'edit_due_date_{todo_id}')
        
        d_day_count = (due_date_input - today_local).days
        
        d_day_input = st.number_input(label='남은 일수', value=d_day_count, key=f'edit_d_day_{todo_id}', disabled=True)

        completion_level_input = st.selectbox('완료 레벨', options=options_completion_level, index=0, key='edit_completion_level', help='완료 레벨을 선택하세요')
        
        status_input = st.selectbox('상태', options=['미처리', '연습중', '예정'], index=['미처리', '연습중', '예정'].index(selected_data['status'].iloc[0]) if 'status' in selected_data else 0, key='edit_status_input', help='상태를 선택하세요')

        st.markdown("---")
        st.markdown("<h3 style='text-align: center; color: red;'>기록 변경</h3>", unsafe_allow_html=True)
        if start_date_input > today_local:
            last_completion_date_input = None
            last_completion_date_disabled = True
        else:
            last_completion_date_disabled = False
        
        last_completion_date_input = st.date_input(label='최근 완료일', value=last_completion_date_local if last_completion_date_local is not None else today_local, 
            key=f'edit_last_completion_date_{todo_id}', help='최근 완료일을', disabled=True)

        completion_count_input = st.number_input(label='완료 횟수', value=int(selected_data['completion_count'].iloc[0]) if 'completion_count' in selected_data else 0, 
                        min_value=0, key=f'edit_completion_count_{todo_id}', disabled=True)
        
        accumulated_min_input = st.number_input(label='누적 (분)', value=int(selected_data['accumulated_min'].iloc[0]) if 'accumulated_min' in selected_data else 0, 
                        min_value=0, key=f'edit_accumulated_min_{todo_id}', disabled=True)
        
        if start_date_input <= today_local:
            add_completion_date_input = st.date_input(label='완료일 추가', value=None,
                min_value=start_date_input, max_value=today_local, key=f'edit_add_completion_date_{todo_id}', help='완료일을 추가 할 수 있습니다.', disabled=last_completion_date_disabled)
            add_accumulated_min_input = st.number_input(label='누적 (분)', value=1, min_value=1, key=f'edit_add_accumulated_min_{todo_id}', disabled=add_completion_date_input is None)
        else:
            add_completion_date_input = None
            add_accumulated_min_input = 0

        start_timestamp_utc = convertTo_timestamp_utc(start_date_input)

       
        last_completion_timestamp_utc = convertTo_timestamp_utc(last_completion_date_input) if last_completion_date_input else None


        
        if last_completion_timestamp_utc is None:
            due_timestamp_utc = max(convertTo_timestamp_utc(due_date_input), start_timestamp_utc + repeat_cycle_input * 24 * 60 * 60)
        else:
            due_timestamp_utc = max(convertTo_timestamp_utc(due_date_input), last_completion_timestamp_utc + repeat_cycle_input * 24 * 60 * 60)

        

                
        if st.button('저장', key=f'edit_save_{todo_id}'):
            if title_input != "":
                st.session_state.formState_editToDo = 'close'

                if add_completion_date_input is not None:
                    accumulated_min_input += add_accumulated_min_input
                    completion_count_input += 1
                    accumulated_min_input += add_accumulated_min_input

                
                df_edited_todo = pd.DataFrame({
                            'id': [selected_data['id'].iloc[0]],
                            'title': [title_input],
                            'repeat_cycle': [repeat_cycle_input],
                            'continuous_count_perCycle': [continuous_count_perCycle_input], 
                            'accumulated_min': [accumulated_min_input], 
                            'completion_count': [completion_count_input],

                            'start_timestamp_utc': [start_timestamp_utc],
                            'last_completion_timestamp_utc': [last_completion_timestamp_utc],
                            'due_timestamp_utc': [due_timestamp_utc],

                            'completion_level': [completion_level_input],
                            'status': [status_input],

                            # 자동 계산
                            'd_day_local': [d_day_count],            
                            'days_elapsed': [None], 

                        })

                update_db_todo(df_edited_todo)
                st.rerun()
            else:
                st.error('곡명을 입력하세요')



# 데이터 정보 표시 함수
def show_data_info(selected_data):
    global today_local
    start_date_local = convertTo_localDate(selected_data['start_timestamp_utc'].iloc[0])
    last_completion_date_local = convertTo_localDate(selected_data['last_completion_timestamp_utc'].iloc[0])
    due_date_local = convertTo_localDate(selected_data['due_timestamp_utc'].iloc[0])
    d_day_local = int((due_date_local - today_local).days) * -1

    accumulated_hour = round(selected_data['accumulated_min'].iloc[0] / 60, 1)
    st.markdown(
        f"<div style='line-height: 1.5;'><span style='color: white; font-size: 14px;'>{str(start_date_local) + ' ~ ' + str(last_completion_date_local)} </span>"
        f"<span style='color: gray; font-size: 14px;'>{'(연속 ' + str(selected_data['repeat_cycle'].iloc[0]) + '회 / ' + str(selected_data['repeat_cycle'].iloc[0]) + '일 간격)'} </span>"
        f"<span style='color: {'red' if d_day_local > 0 else ('green' if d_day_local < 0 else 'yellow')}; "
        f"font-size: 24px;'>   {'D+' + str(abs(d_day_local)) if d_day_local > 0 else ('D-' + str(abs(d_day_local)) if d_day_local < 0 else 'D-Day')}</span></div>", 
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div style='line-height: 1.5;'><span style='color: white; font-size: 14px;'>{'누적: ' + str(accumulated_hour) + 'h'} </span>"
        f"<span style='color: white; font-size: 14px;'>   {'완료: ' + str(selected_data['completion_count'].iloc[0]) + '회'} </span>"
        f"<span style='color: white; font-size: 14px;'>   {'최근: ' + '3' + '일 전'} </span></div>",
        unsafe_allow_html=True
    )



# 선택된 행 표시 함수
@st.fragment
def show_selected_row(selected_data):
    button_style = f"""
    <style>
    div.stButton > button[key="edit_button_{selected_data['id'].iloc[0]}"] {{
        color: yellow !important;
    }}
    </style>
    """
    st.markdown(button_style, unsafe_allow_html=True)

    # 편집 버튼
    if st.button(str(selected_data['title'].iloc[0]), key=f"edit_button_{selected_data['id'].iloc[0]}"):
        if st.session_state.formState_editToDo == 'close':
            st.session_state.formState_editToDo = 'open'
        else:
            st.session_state.formState_editToDo = 'close'

    
    if st.session_state.formState_editToDo == 'open':
        show_edit_form(selected_data)
    else:
        show_data_info(selected_data)
        st.markdown("<hr>", unsafe_allow_html=True)
        show_stopWatch(selected_data['id'].iloc[0])
    







@st.fragment
def show_list_todo(status, key):
    global today_local

    if 'due_timestamp_utc' in df_todo.columns:
        due_date_local = df_todo['due_timestamp_utc'].apply(convertTo_localDate)
    else:
        due_date_local = None

    # due_date_local(Series)와 today_local(scalar) 간의 날짜 차이를 계산
    if due_date_local is not None:
        d_day_local = (due_date_local - today_local).apply(lambda x: x.days if pd.notna(x) else None)
        d_day_local = d_day_local * -1
    else:
        d_day_local = None

    
    if status == '추가':
        df_filtered_todo = df_todo[df_todo['status'] == '미처리'].copy()  # copy() 추가
    else:
        df_filtered_todo = df_todo[df_todo['status'] == status].copy()    # copy() 추가

    df_filtered_todo['d_day_local'] = d_day_local



    # GridOptionsBuilder 설정
    gb = GridOptionsBuilder.from_dataframe(df_filtered_todo[['title', 'd_day_local']])
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(
        domLayout='normal',
        rowSelection="single",
        suppressRowClickSelection=False,
        suppressAutoSize=True,
        suppressColumnVirtualisation=True,
        suppressMenu=True,
        suppressHorizontalScroll=True
    )
    
    # 'title' 열 설정
    gb.configure_column(
        "title",
        headerName="곡목",
        width=360,
        maxWidth=360,
        minWidth=360,
        resizable=False,
        sortable=False,
        filter=False,
        suppressMovable=True,
        suppressSizeToFit=True,
        suppressMenu=True,
        cellStyle={"color": "white"}  # 글자색 흰색으로 설정
    )
    
    # 'd_day_local' 열 설정 (조건부 색상 적용)
    gb.configure_column(
        "d_day_local",
        headerName="D-Day",
        width=100,
        maxWidth=100,
        minWidth=100,
        resizable=False,
        sortable=False,
        filter=False,
        suppressMovable=True,
        suppressSizeToFit=True,
        suppressMenu=True,
        type=["numericColumn"],  # 숫자형 열로 처리
        cellClassRules={
            "yellow": "value == 0",  # D-Day가 0일 때 노란색
            "green": "value < 0",    # D-Day가 음수일 때 초록색
            "red": "value > 0"       # D-Day가 양수일 때 빨간색
        }
    )

    # 그리드 높이 설정
    row_height = 30
    header_height = 40
    fixed_rows = 8
    grid_height = header_height + (row_height * fixed_rows)

    # 커스텀 CSS 정의
    custom_css = {
        ".ag-root-wrapper": {"overflow-x": "hidden", "margin-bottom": "0px"},
        ".ag-body-horizontal-scroll": {"display": "none"},
        ".ag-cell.yellow": {"color": "yellow !important"},  # 노란색 클래스
        ".ag-cell.green": {"color": "green !important"},    # 초록색 클래스
        ".ag-cell.red": {"color": "red !important"}         # 빨간색 클래스
    }

    # AgGrid 렌더링
    grid_response = AgGrid(
        df_filtered_todo[['title', 'd_day_local']],
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,  # JavaScript 조건 허용
        height=grid_height,
        custom_css=custom_css,
        fit_columns_on_grid_load=False,
        key=f"aggrid_{status}"
    )

    # 선택된 행 처리
    if grid_response['selected_rows'] is not None:
        st.session_state.show_selected_row = True
        selected_title = grid_response['selected_rows'].iloc[0]['title']
        df_todo_selected = df_todo[df_todo['title'] == selected_title]
        if not df_todo_selected.empty and status == '연습중':
            show_selected_row(df_todo_selected.head(1))
    else:
        st.session_state.show_selected_row = False





    


@st.fragment(run_every=10)
def show_main_form(status):
    global today_local
    today_local = get_today_local()
    # last_completion_date_local = convertTo_localDate(df_todo['last_completion_timestamp_utc'])
    # due_date_local = convertTo_localDate(df_todo['due_timestamp_utc'])
    # d_day_local = int((due_date_local - today_local).days)

    # df_todo['d_day_local'] = -1 * (df_todo.apply(lambda row: (row['due_date_local'] - today_local).days, axis=1))
    # update_db_todo(df_todo)



    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(["TODAY", "연습중", "/", "예정", "보류", '미처리', '   /   ', 'level1', 'level2', 'level3'])
    with tab1:
        show_list_todo(status='연습중', key='aggrid_연습중')

    with tab2:
        show_list_todo(status='예정', key='aggrid_예정')

    with tab3:
        st.session_state.show_selected_row = False
        show_list_todo(status='미처리', key='aggrid_미처리')

    with tab4:
        pass

    with tab5:
        show_list_todo(status='추가', key='aggrid_추가')

    # st.rerun()


with st.sidebar:
    if st.button('곡 추가'):
        st.session_state.formState_addToDo = 'open'
        add_todo()
    else:
        add_todo()











def main_app():
    show_main_form(status='연습중')

# # 앱 실행
main_app()