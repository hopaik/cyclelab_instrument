import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from Levenshtein import distance as levenshtein_distance
import time
import datetime
import threading
import streamlit.components.v1 as components

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
if 'formState_completeTodo' not in st.session_state:
    st.session_state.formState_completeTodo = 'close'






options_genre = ['장르1', '장르2', '장르3']
options_style1 = ['스타일1', '스타일2', '스타일3']
options_style2 = ['스타일4', '스타일5', '스타일6']
options_key1 = ['키1', '키2', '키3']
options_key2 = ['키4', '키5', '키6']
options_completion_level = ['Level_0', 'Level_1', 'Level_2', 'Level_3']



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
        ['title', 'start_date', 'end_date', 'repeat_cycle', 'D_Day', 'days_elapsed', 'accumulated_time', 'completion_count', 'status', 'continuous_count_perCycle', 'completion_level', 'stopWatch'],
        """
        CREATE TABLE IF NOT EXISTS todo (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            start_date DATE,
            end_date DATE,
            repeat_cycle INT,
            continuous_count_perCycle INT,
            D_Day INT, 
            days_elapsed INT,
            accumulated_time INT,
            completion_count INT,
            status VARCHAR(255),
            completion_level VARCHAR(255),
            stopWatch VARCHAR(255)
        )
        """
    )
    return df_todo

df_todo = load_from_db()



def update_db_todo(new_data):
    global df_todo
    if df_todo.empty:
        df_todo = new_data
    elif new_data["id"].iloc[0] in df_todo["id"].values:
        df_todo.loc[df_todo["id"] == new_data["id"].iloc[0]] = new_data
    else:
        df_todo = pd.concat([df_todo, new_data], ignore_index=True)

    try:
        df_todo.to_sql('todo', con=engine_mainDB, if_exists='replace', index=False)
        st.success('업데이트 되었습니다')
        st.rerun()
    except Exception as e:
        st.error('데이터 저장 중 오류가 발생했습니다.')
        return False




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
            continuous_count_perCycle = int(st.number_input('연속일 횟수', min_value=1, value=1, key='continuous_count_perCycle', help='반복주기마다 수행해야 할 연속일 횟수를 입력하세요', step=1))
        col4 = st.columns(2)
        with col4[0]:
            start_date_input = st.date_input('시작일 (예정일)', value=pd.to_datetime('today').date(), min_value=pd.to_datetime('today').date(), key='start_date_input', help='시작일을 선택하세요')
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

                    # 일련번호 생성
                    if df_todo.empty:
                        new_id = 1
                    else:
                        new_id = df_todo['id'].max() + 1

                    # 새로운 데이터 생성
                    new_todo = pd.DataFrame({
                        'id': [new_id],
                        'title': [title_input],                                    #곡목
                        'repeat_cycle': [repeat_cycle_input],                      #반복주기
                        'continuous_count_perCycle': [continuous_count_perCycle],  #연속횟수 (반복주기당 연속 수행할 횟수)
                        'start_date': [start_date_input],                          #시작일
                        'completion_level': [completion_level],                    #완료 레벨
                        'status': [status_input],                                  #상태 (미처리, 연습중, 예정)

                        'D_Day': [0],                                              #[자동] D-Day                           
                        'end_date': [start_date_input],                            #[자동] 종료일                           
                        'days_elapsed': [0],                                       #[자동] 최근 연습이후 경과일
                        'accumulated_time': [0],                                   #[자동] 연습 누적시간
                        'completion_count': [0],                                   #[자동] 연습 완료횟수
                        'stopWatch': [''],                                         #[자동] 진행 상태 시간 
    
                        # 'genre': [options_genre],                                 #장르
                        # 'style1': [options_style1],                               #스타일1
                        # 'style2': [options_style2],                               #스타일2
                        # 'key1': [options_key1],                                   #키1
                        # 'key2': [options_key2],                                   #키2

                    })

                    update_db_todo(new_todo)
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
        st.session_state[f'start_time_{todo_id}'] = datetime.datetime.now()
    if f'running_{todo_id}' not in st.session_state:
        st.session_state[f'running_{todo_id}'] = False
    if f'elapsed_time_{todo_id}' not in st.session_state:
        st.session_state[f'elapsed_time_{todo_id}'] = 0
    if f'timer_last_updated_{todo_id}' not in st.session_state:
        st.session_state[f'timer_last_updated_{todo_id}'] = datetime.datetime.now()
    

    def update_elapsed_time():
        if st.session_state[f'running_{todo_id}']:
            current_time = datetime.datetime.now()
            time_diff = current_time - st.session_state[f'timer_last_updated_{todo_id}']
            st.session_state[f'elapsed_time_{todo_id}'] += time_diff.seconds
            st.session_state[f'timer_last_updated_{todo_id}'] = current_time

    def toggle_timer():
        if st.session_state[f'running_{todo_id}']:
            update_elapsed_time()
            st.session_state[f'running_{todo_id}'] = False
        else:
            st.session_state[f'timer_last_updated_{todo_id}'] = datetime.datetime.now()
            st.session_state[f'running_{todo_id}'] = True

    def reset_timer():
        st.session_state[f'elapsed_time_{todo_id}'] = 0
        st.session_state[f'running_{todo_id}'] = False
        st.session_state[f'timer_last_updated_{todo_id}'] = datetime.datetime.now()




    def complete_todo():
        update_elapsed_time()
        elapsed_time = st.session_state[f'elapsed_time_{todo_id}']
        hours = elapsed_time // 3600
        minutes = (elapsed_time % 3600) // 60
        seconds = elapsed_time % 60
        stopWatch = f"{hours:02}:{minutes:02}:{seconds:02}"
        st.session_state.formState_completeTodo = 'open'
        df_todo.loc[df_todo['id'] == todo_id, 'stopWatch'] = stopWatch
        update_db_todo(df_todo)
        reset_timer()


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
                     on_click=complete_todo,
                     use_container_width=True)

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
    todo_id = selected_data["id"].iloc[0]
    with st.container(key=f'edit_form_{todo_id}'):
        col1 = st.columns(1)
        with col1[0]:
            title_input = st.text_input(label='title', value=selected_data['title'].iloc[0] if 'title' in selected_data else None, 
                          key=f'selected_data_title_{todo_id}')
        col2 = st.columns(2)
        with col2[0]:
            D_Day_input = st.text_input(label='D_Day', value=selected_data['D_Day'].iloc[0] if 'D_Day' in selected_data else None, 
                          key=f'selected_data_D_Day_{todo_id}')
        with col2[1]:
            start_date_input = st.date_input(label='start_date', value=pd.to_datetime(selected_data['start_date'].iloc[0]) if 'start_date' in selected_data else None, 
                          key=f'selected_data_start_date_{todo_id}')
        col3 = st.columns(3)
        with col3[0]:
            days_elapsed_input = st.text_input(label='days_elapsed', value=selected_data['days_elapsed'].iloc[0] if 'days_elapsed' in selected_data else None, 
                          key=f'selected_data_days_elapsed_{todo_id}')
        with col3[1]:
            accumulated_time_input = st.text_input(label='accumulated_time', value=selected_data['accumulated_time'].iloc[0] if 'accumulated_time' in selected_data else None, 
                          key=f'selected_data_accumulated_time_{todo_id}')
        with col3[2]:
            completion_count_input = st.number_input(label='completion_count', value=selected_data['completion_count'].iloc[0] if 'completion_count' in selected_data else None, 
                            min_value=0, key=f'selected_data_completion_count_{todo_id}', disabled=False)
                
        if st.button('저장', key=f'selected_data_save_{todo_id}'):
            if title_input != "":
                st.session_state.formState_editToDo = 'close'

                edited_todo = pd.DataFrame({
                            'id': [selected_data['id'].iloc[0]],
                            'title': [title_input],
                            'repeat_cycle': [selected_data['repeat_cycle'].iloc[0]],
                            'continuous_count_perCycle': [selected_data['continuous_count_perCycle'].iloc[0]], 
                            'start_date': [start_date_input], 
                            'completion_level': [selected_data['completion_level'].iloc[0]],
                            'status': [selected_data['status'].iloc[0]],

                            # 자동 계산
                            'D_Day': [D_Day_input], 
                            'end_date': [start_date_input], 
                            'days_elapsed': [days_elapsed_input], 
                            'accumulated_time': [accumulated_time_input], 
                            'completion_count': [completion_count_input],
                            'stopWatch': [selected_data['stopWatch'].iloc[0]],

                        })
        

                update_db_todo(edited_todo)
            else:
                st.error('곡명을 입력하세요')



# 데이터 정보 표시 함수
def show_data_info(selected_data):
    st.markdown(
        f"<div style='line-height: 1.5;'><span style='color: white; font-size: 14px;'>{str(selected_data['start_date'].iloc[0]) + ' ~ ' + str(selected_data['start_date'].iloc[0])} </span>"
        f"<span style='color: gray; font-size: 14px;'>{'(연속 ' + str(selected_data['repeat_cycle'].iloc[0]) + '회 / ' + str(selected_data['repeat_cycle'].iloc[0]) + '일 간격)'} </span>"
        f"<span style='color: red; font-size: 24px;'>   {'D+' + str(selected_data['D_Day'].iloc[0]) if int(selected_data['D_Day'].iloc[0]) > 0 else ('D' + str(selected_data['D_Day'].iloc[0]) if int(selected_data['D_Day'].iloc[0]) < 0 else 'D-Day')}</span></div>", 
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div style='line-height: 1.5;'><span style='color: white; font-size: 14px;'>{'누적: ' + str(selected_data['accumulated_time'].iloc[0]) + 'h'} </span>"
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
        if st.session_state.formState_completeTodo == 'open':
            st.write("Completed!!")
            st.session_state.formState_completeTodo = 'close'
        else:
            show_data_info(selected_data)
            st.markdown("<hr>", unsafe_allow_html=True)
            show_stopWatch(selected_data['id'].iloc[0])






@st.fragment
def show_list_todo(status, key):
    if status == '추가':
        df_filtered_todo = df_todo[df_todo['status'] == '미처리']
    else:
        df_filtered_todo = df_todo[df_todo['status'] == status]

    gb = GridOptionsBuilder.from_dataframe(df_filtered_todo[['title', 'D_Day']])
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
    gb.configure_column(
        "title",
        headerName="Title",
        width=360,
        maxWidth=360,
        minWidth=360,
        resizable=False,
        sortable=False,
        filter=False,
        suppressMovable=True,
        suppressSizeToFit=True,
        suppressMenu=True
    )
    gb.configure_column(
        "D_Day",
        headerName="D-Day",
        width=100,
        maxWidth=100,
        minWidth=100,
        resizable=False,
        sortable=False,
        filter=False,
        suppressMovable=True,
        suppressSizeToFit=True,
        suppressMenu=True
    )

    row_height = 30
    header_height = 40
    fixed_rows = 8
    grid_height = header_height + (row_height * fixed_rows)

    custom_css = {
        ".ag-root-wrapper": {"overflow-x": "hidden", "margin-bottom": "0px"},
        ".ag-body-horizontal-scroll": {"display": "none"},
    }

    grid_response = AgGrid(
        df_filtered_todo[['title', 'D_Day']],
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,  # VALUE_CHANGED 제거
        allow_unsafe_jscode=True,
        height=grid_height,
        custom_css=custom_css,
        fit_columns_on_grid_load=False,
        key=f"aggrid_{status}"
    )

    if grid_response['selected_rows'] is not None:
        st.session_state.show_selected_row = True
        selected_title = grid_response['selected_rows'].iloc[0]['title']
        df_todo_selected = df_todo[df_todo['title'] == selected_title]
        if not df_todo_selected.empty and status == '연습중':
            show_selected_row(df_todo_selected.head(1))
    else:
        st.session_state.show_selected_row = False

    return False





with st.sidebar:
    if st.button('곡 추가'):
        st.session_state.formState_addToDo = 'open'
        add_todo()
    else:
        add_todo()
    


def show_main_form(status):
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["연습중", "예정", "미처리", "/", "추가"])
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



# Streamlit 앱
def main_app():
    show_main_form(status='연습중')


# 앱 실행
main_app()
