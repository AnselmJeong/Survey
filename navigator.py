import streamlit as st


def generate_navigator(sss, callback=None):
    answer = 0

    def _next():
        bound = len(sss["IDs"]) - 1
        sss["current_index"] = min(sss["current_index"] + 1, bound)
        callback()

    def _prev():
        bound = 0
        sss["current_index"] = max(sss["current_index"] - 1, bound)
        callback()

    with st.container():
        col1, col2, col3 = st.columns([0.25, 0.5, 0.25])
        col1.button(
            "이전환자",
            on_click=_prev,
            type="primary",
            use_container_width=True,
            disabled=sss["current_index"] == 0,
        )

        col2.selectbox(
            "Select ID:",
            range(len(sss["IDs"])),
            key="current_index",
            format_func=lambda x: f'{x:02d}: {sss["IDs"][x]}',
            label_visibility="collapsed",
            on_change=callback,
        )

        col3.button(
            "다음환자",
            on_click=_next,
            type="primary",
            use_container_width=True,
            disabled=sss["current_index"] == len(sss["IDs"]) - 1,
        )
