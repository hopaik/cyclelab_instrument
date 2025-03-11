import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from Levenshtein import distance as levenshtein_distance
import time


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

st.subheader('CycleLab - 악기 연습')


# 선택된 행이 있을 경우 상세 정보 출력
def show_selected_row(selected_data):
    st.session_state.formState_selected_row = 'open'
    st.write("상세 정보:")
    print(selected_data['title'])
    
    # 고유한 키 생성을 위한 타임스탬프 추가
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
            # st.rerun()
    with col4[1]:
        if st.button('닫기', key=f'selected_data_close_{timestamp}'):
            st.session_state.show_selected_row = False
            st.session_state.formState_editToDo = 'close'
            print('닫기')
            print(st.session_state.show_selected_row)
            st.session_state.formState_selected_row = 'close'
            return

        
    



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
            status_input = st.selectbox('상태', options=['미처리', '연습중', '완료', '예정'], index=0, key='status_input', help='상태를 선택하세요')
        col6 = st.columns(4)
        with col6[2]:
            if st.button('저장'):
                if title_input != "":
                    st.session_state.formState_addToDo = 'close'
                    st.session_state.show_title_form = False

                    # 새로운 데이터 생성
                    df_new_todo = pd.DataFrame({
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
                        # st.rerun()
                    else:
                        st.error('데이터 저장 중 오류가 발생했습니다.')
                else:
                    st.error('곡명을 입력하세요')
        with col6[3]:
            if st.button('취소'):
                st.session_state.formState_addToDo = 'close'
                st.session_state.show_title_form = False
                # st.rerun()



def show_list_todo(status):
    if status == '추가':
        df_filtered_todo = df_todo[df_todo['status'] == '미처리']
    else:
        df_filtered_todo = df_todo[df_todo['status'] == status]

    # GridOptionsBuilder 설정
    gb = GridOptionsBuilder.from_dataframe(df_filtered_todo[['title', 'D_Day']])
    gb.configure_selection(selection_mode="single", use_checkbox=False)  # 단일 행 선택, 체크박스 제거
    
    # 그리드 전체 옵션 설정
    gb.configure_grid_options(
        domLayout='autoHeight',
        rowSelection="single",
        suppressRowClickSelection=False,  # 행 클릭으로 선택 가능
        suppressAutoSize=True,
        suppressColumnVirtualisation=True,
        suppressMenu=True
    )

    # 컬럼 설정
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

    # AgGrid 렌더링 및 선택된 행 반환
    grid_response = AgGrid(
        df_filtered_todo[['title', 'D_Day']],
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,  # 선택 및 값 변경 감지
        allow_unsafe_jscode=True,
        height=300,
        fit_columns_on_grid_load=False,
        key=f"aggrid_{status}"  # 고유한 키 사용
    )



    # 선택된 행 가져오기
    if grid_response['selected_rows'] is not None:
        st.session_state.show_selected_row = True
        selected_title = grid_response['selected_rows'].iloc[0]['title']
        df_todo_selected = df_todo[df_todo['title'] == selected_title]
    else:
        df_todo_selected = pd.DataFrame()


    print(df_todo_selected)
    print(st.session_state.show_selected_row)
    print(st.session_state.formState_selected_row)


    if not df_todo_selected.empty and st.session_state.show_selected_row == True:
        if st.session_state.show_selected_row == True and st.session_state.formState_selected_row == 'close':
            show_selected_row(df_todo_selected.head(1))
    
    return False





with st.sidebar:
    st.header("추가, 편집")


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["연습중", "완료", "예정", "미처리", "/", "추가"])
with tab1:
    show_list_todo(status='연습중')

with tab2:
    show_list_todo(status='완료')

with tab3:
    show_list_todo(status='예정')

with tab4:
    st.session_state.show_selected_row = False
    show_list_todo(status='미처리')

with tab5:
    pass

with tab6:
    show_list_todo(status='추가')


if st.session_state.formState_addToDo == 'close':
    if st.button('추가'):
        st.session_state.formState_addToDo = 'open'
        add_todo()
else:
    add_todo()


