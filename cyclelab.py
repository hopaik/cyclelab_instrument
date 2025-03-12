import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from Levenshtein import distance as levenshtein_distance
import time
import datetime
import threading
import streamlit.components.v1 as components

# Set the theme to night mode
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

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
# if 'formState_editToDo' not in st.session_state:
#     st.session_state.formState_editToDo = 'close'
if 'show_title_form' not in st.session_state:
    st.session_state.show_title_form = False
if 'show_selected_row' not in st.session_state:
    st.session_state.show_selected_row = False
if 'formState_selected_row' not in st.session_state:
    st.session_state.formState_selected_row = 'close'


genre_options = ['장르1', '장르2', '장르3']
style1_options = ['스타일1', '스타일2', '스타일3']
style2_options = ['스타일4', '스타일5', '스타일6']
key1_options = ['키1', '키2', '키3']
key2_options = ['키4', '키5', '키6']

# st.subheader('CycleLab - 악기 연습')


def update_db(dataframe_name, dataframe):
    try:
        if dataframe_name == 'todo':
            dataframe.to_sql('todo', con=engine_mainDB, if_exists='replace', index=False)
            return True
        else:
            return False
    except Exception as e:
        print(f"에러 발생: {e}")
        return False



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
        ['title', 'start_date', 'repeat_cycle', 'D_Day', 'days_elapsed', 'accumulated_time', 'completion_count', 'status'],
        """
        CREATE TABLE IF NOT EXISTS todo (
            title VARCHAR(255),
            start_date DATE,
            repeat_cycle INT,
            D_Day INT, 
            days_elapsed INT,
            accumulated_time INT,
            completion_count INT,
            status VARCHAR(255)
        )
        """
    )
    return df_todo

df_todo = load_from_db()


def add_todo():
    global df_todo
    global locate_doto

    if st.session_state.formState_addToDo == 'open':
        col2 = st.columns(1)
        with col2[0]:
            title_input = st.text_input('곡명', value="", key='title_input', help='곡명을 입력하세요')
        col3 = st.columns(2)
        with col3[0]:
            repeat_cycle_input = int(st.number_input('반복주기 (일)', min_value=1, value=1, key='repeat_cycle_input', help='반복주기(일)를 입력하세요', step=1))
        with col3[1]:
            start_date_input = st.date_input('시작일', value=pd.to_datetime('today').date(), key='start_date_input', help='시작일을 선택하세요')
        col4 = st.columns(2)
        with col4[0]:
            status_input = st.selectbox('상태', options=['미처리', '연습중', '예정'], index=0, key='status_input', help='상태를 선택하세요')
        col6 = st.columns(4)
        with col6[2]:
            if st.button('저장'):
                if title_input != "":
                    st.session_state.formState_addToDo = 'close'
                    st.session_state.show_title_form = False

                    # 일련번호 생성
                    if df_todo.empty:
                        new_id = 1
                    else:
                        new_id = df_todo['id'].max() + 1

                    # 새로운 데이터 생성
                    df_new_todo = pd.DataFrame({
                        'id': [new_id],
                        'title': [title_input],
                        'D_Day': [0], 
                        'start_date': [start_date_input], 
                        'repeat_cycle': [repeat_cycle_input],
                        'days_elapsed': [0], 
                        'accumulated_time': [0], 
                        'completion_count': [0],
                        'status': [status_input]
                    })

                    # 기존 DataFrame이 존재하는지 확인
                    if df_todo.empty:
                        df_todo = df_new_todo
                    else:
                        df_todo = pd.concat([df_todo, df_new_todo], ignore_index=True)

                    # DB 업데이트 및 상태 변경
                    if update_db('todo', df_todo):
                        st.success('목록에 추가되었습니다')
                        st.rerun()
                    else:
                        st.error('데이터 저장 중 오류가 발생했습니다.')
                else:
                    st.error('곡명을 입력하세요')
        with col6[3]:
            if st.button('취소'):
                st.session_state.formState_addToDo = 'close'
                st.session_state.show_title_form = False
                st.rerun()




@st.fragment
def show_stopWatch(todo_id):  # todo_id 추가
    # 초기화 (세션 상태 키에 todo_id 추가)
    if f'start_time_{todo_id}' not in st.session_state:
        st.session_state[f'start_time_{todo_id}'] = datetime.datetime.now()
    if f'running_{todo_id}' not in st.session_state:
        st.session_state[f'running_{todo_id}'] = False
    if f'elapsed_time_{todo_id}' not in st.session_state:
        st.session_state[f'elapsed_time_{todo_id}'] = 0
    if f'timer_last_updated_{todo_id}' not in st.session_state:
        st.session_state[f'timer_last_updated_{todo_id}'] = datetime.datetime.now()

    # 타이머 업데이트 함수
    def update_elapsed_time():
        if st.session_state[f'running_{todo_id}']:
            current_time = datetime.datetime.now()
            time_diff = current_time - st.session_state[f'timer_last_updated_{todo_id}']
            st.session_state[f'elapsed_time_{todo_id}'] += time_diff.seconds
            st.session_state[f'timer_last_updated_{todo_id}'] = current_time

    # 타이머 시작/정지 함수
    def toggle_timer():
        if st.session_state[f'running_{todo_id}']:
            update_elapsed_time()
            st.session_state[f'running_{todo_id}'] = False
        else:
            st.session_state[f'timer_last_updated_{todo_id}'] = datetime.datetime.now()
            st.session_state[f'running_{todo_id}'] = True

    # 타이머 리셋 함수
    def reset_timer():
        st.session_state[f'elapsed_time_{todo_id}'] = 0
        st.session_state[f'running_{todo_id}'] = False
        st.session_state[f'timer_last_updated_{todo_id}'] = datetime.datetime.now()

    def settle_timer():
        # st.session_state[f'elapsed_time_{todo_id}'] = 0
        # st.session_state[f'running_{todo_id}'] = False
        # st.session_state[f'timer_last_updated_{todo_id}'] = datetime.datetime.now()
        return


    if st.session_state[f'running_{todo_id}']:
        update_elapsed_time()

    #스톱워치 표시
    hours = st.session_state[f'elapsed_time_{todo_id}'] // 3600
    minutes = (st.session_state[f'elapsed_time_{todo_id}'] % 3600) // 60
    seconds = st.session_state[f'elapsed_time_{todo_id}'] % 60
    timer_display = f"{hours:02}:{minutes:02}:{seconds:02}"
    
    timer_html = f"""
    <div id="timer_{todo_id}" style="font-size: 48px; font-weight: bold; color: #FF0000;">
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

    # 버튼을 하나의 컨테이너로 묶어 한 행에 표시
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("정지" if st.session_state[f'running_{todo_id}'] else "시작", 
                     key=f'toggle_button_{todo_id}',  # 고유 키
                     on_click=toggle_timer,
                     use_container_width=True)
        with col2:
            st.button("리셋", 
                     key=f'reset_button_{todo_id}',  # 고유 키
                     on_click=reset_timer,
                     use_container_width=True)
        with col3:
            st.button("정산", 
                     key=f'settle_button_{todo_id}',  # 고유 키
                     on_click=settle_timer,
                     use_container_width=True)

    st.markdown("""
    <style>
    div[data-testid="column"] button {
        padding: 2.5px 1.25px;  /* 좌우 5px -> 2.5px로 반으로 축소 */
        font-size: 12px;        /* 폰트 크기 작게 */
        height: 20px;           /* 높이 작게 */
        width: 25%;             /* 너비 작게 */
        min-width: 10px;        /* 최소 너비 작게 */
    }
    </style>
    """, unsafe_allow_html=True)




def show_data_info(selected_data):
    with st.container(key=f'data_info_{selected_data["id"].iloc[0]}'):
        st.markdown(
            f"<div style='line-height: 0.75;'><span style='color: yellow; font-size: 18px;'>{str(selected_data['title'].iloc[0])} </span>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='line-height: 1.5;'><span style='color: white; font-size: 14px;'>{str(selected_data['start_date'].iloc[0]) + ' ~ ' + str(selected_data['start_date'].iloc[0])} </span>"
            f"<span style='color: gray; font-size: 14px;'>{'(연속 ' + str(selected_data['repeat_cycle'].iloc[0]) + '회 / ' + str(selected_data['repeat_cycle'].iloc[0]) + '일 간격)'} </span>"
            f"<span style='color: red; font-size: 24px;'>   {'D+' + str(selected_data['D_Day'].iloc[0]) if selected_data['D_Day'].iloc[0] > 0 else ('D' + str(selected_data['D_Day'].iloc[0]) if selected_data['D_Day'].iloc[0] < 0 else 'D-Day')}</span></div>", 

            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='line-height: 1.5;'><span style='color: white; font-size: 14px;'>{'누적: ' + str(selected_data['accumulated_time'].iloc[0]) + 'h'} </span>"
            f"<span style='color: white; font-size: 14px;'>   {'완료: ' + str(selected_data['completion_count'].iloc[0]) + '회'} </span>"
            f"<span style='color: white; font-size: 14px;'>   {'최근: ' + '3' + '일 전'} </span></div>",
            unsafe_allow_html=True
        )

    
    

def show_selected_row(selected_data):
    show_data_info(selected_data)
    
    # 현재 선택된 todo_id
    new_todo_id = selected_data['id'].iloc[0]

    # 이전에 선택된 todo_id가 있고, 새로운 id와 다를 경우 이전 타이머 일시정지
    if 'current_todo_id' in st.session_state and st.session_state['current_todo_id'] != new_todo_id:
        old_todo_id = st.session_state['current_todo_id']
        if f'running_{old_todo_id}' in st.session_state and st.session_state[f'running_{old_todo_id}']:
            # 이전 타이머가 실행 중이면 시간 업데이트 후 정지
            current_time = datetime.datetime.now()
            time_diff = current_time - st.session_state[f'timer_last_updated_{old_todo_id}']
            st.session_state[f'elapsed_time_{old_todo_id}'] += time_diff.seconds
            st.session_state[f'timer_last_updated_{old_todo_id}'] = current_time
            st.session_state[f'running_{old_todo_id}'] = False

    # 현재 todo_id 업데이트
    st.session_state['current_todo_id'] = new_todo_id
    st.session_state.formState_selected_row = 'open'
    
    # 'id'를 사용하여 타이머 호출
    todo_id = new_todo_id
    show_stopWatch(todo_id)
    
    st.write("상세 정보:")
    print(selected_data['title'])
    
    timestamp = int(time.time() * 1000)
    
    col1 = st.columns(1)
    with col1[0]:
        st.text_input(label='title', value=selected_data['title'].iloc[0] if 'title' in selected_data else None, 
                     key=f'selected_data_title_{timestamp}')
    
    col2 = st.columns(2)
    with col2[0]:
        st.text_input(label='D_Day', value=selected_data['D_Day'].iloc[0] if 'D_Day' in selected_data else None, 
                     key=f'selected_data_D_Day_{timestamp}')
    with col2[1]:
        st.date_input(label='start_date', value=pd.to_datetime(selected_data['start_date'].iloc[0]) if 'start_date' in selected_data else None, 
                     key=f'selected_data_start_date_{timestamp}')
    
    col3 = st.columns(3)
    with col3[0]:
        st.text_input(label='days_elapsed', value=selected_data['days_elapsed'].iloc[0] if 'days_elapsed' in selected_data else None, 
                     key=f'selected_data_days_elapsed_{timestamp}')
    with col3[1]:
        st.text_input(label='accumulated_time', value=selected_data['accumulated_time'].iloc[0] if 'accumulated_time' in selected_data else None, 
                     key=f'selected_data_accumulated_time_{timestamp}')
    with col3[2]:
        st.number_input(label='completion_count', value=selected_data['completion_count'].iloc[0] if 'completion_count' in selected_data else None, 
                       min_value=0, key=f'selected_data_completion_count_{timestamp}', disabled=False)
        
    col4 = st.columns(2)
    with col4[0]:
        if st.button('저장', key=f'selected_data_save_{timestamp}'):
            st.session_state.formState_editToDo = 'close'
            st.session_state.show_selected_row = False
            st.session_state.formState_selected_row = 'close'
            st.rerun()
    with col4[1]:
        if st.button('닫기', key=f'selected_data_close_{timestamp}'):
            st.session_state.show_selected_row = False
            st.session_state.formState_editToDo = 'close'
            print('닫기')
            print(st.session_state.show_selected_row)
            st.session_state.formState_selected_row = 'close'
            return

def show_list_todo(status):
    if status == '추가':
        df_filtered_todo = df_todo[df_todo['status'] == '미처리']

