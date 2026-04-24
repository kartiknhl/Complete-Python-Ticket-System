import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_HOST = st.secrets["DB_HOST"]
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/postgres?sslmode=require"

# Set the layout of the web page
st.set_page_config(page_title="Fest Admin", layout="wide")

st.title("🎟️ Fest Admin Live Dashboard")
st.markdown("Monitor live entry stats and the guest list.")

engine = create_engine(DB_URL)

try:
    # Load the data from the database into a Pandas DataFrame
    df = pd.read_sql_query("SELECT * FROM attendees", engine)

    # Calculate live metrics
    total_registered = len(df)
    total_attended = len(df[df['status'] == 'Attended'])
    total_waiting = total_registered - total_attended

    # Display the metrics in three neat columns
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Registered", total_registered)
    col2.metric("Checked In", total_attended)
    col3.metric("Waiting Outside", total_waiting)

    st.divider()

    with st.expander("🛠️ Advanced Admin Tools", expanded=True):
        st.markdown("Batch delete specific attendees here:")
        if df.empty:
            st.info("No entries available to delete.")
        else:
            attendees_list = [f"{row['name']} ({row['email']})" for _, row in df.iterrows()]
            selected_attendees = st.multiselect("Select Attendees to Remove", attendees_list)
            
            if st.button("Delete Selected Records", type="primary", key="batch_delete"):
                if selected_attendees:
                    with engine.connect() as conn:
                        for attendee in selected_attendees:
                            email = attendee.split("(")[-1].strip(")")
                            conn.execute(
                                text("DELETE FROM attendees WHERE email = :email"),
                                {"email": email}
                            )
                        conn.commit()
                    st.success(f"Successfully deleted {len(selected_attendees)} record(s).")
                    st.rerun()

    st.divider()

    # Display the actual database table so organizers can search names
    st.subheader("Live Guest List")
    # We drop the ticket_id column from the view so the cryptographic hashes stay secret
    display_df = df.drop(columns=['ticket_id'])
    st.dataframe(display_df, width="stretch")

except Exception as e:
    st.error(f"Database error: {e}")

engine.dispose()

# A button to manually refresh the page when new people enter
if st.button("🔄 Refresh Live Data"):
    st.rerun()