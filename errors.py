import traceback

import streamlit as st

def exception_handler(func):
    """
    Returns traceback errors and prints to streamlit.
    """
    def inner_function(*args, **kwargs):
        try:
            returned_value = func(*args, **kwargs)
            return returned_value
        except Exception:

            # traceback.print_exc()
            e = traceback.format_exc()

            error_message = """
            Error occurred - please screenshot this message and reach out to Brandon Cervone (bcervone@webershandwick.com)
            for assistance  \n  \nError Reference: {}
            """.format(e)

            st.error(error_message)

    return inner_function