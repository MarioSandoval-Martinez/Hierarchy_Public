import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

st.set_page_config(layout="wide")

def get_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"]
    )

# Columns to show in detailed view
display_columns = [
    "Enterprise ID", "Account Name", "Record Type ID", "Ultimate Parent Name",
    "Ultimate Parent Enterprise ID", "Billing Street","D&B Connect DUNS Number", "D&B Connect GU DUNS",
    "D&B Connect GU Name","D&B Connect Company Profile","Previous GU DUNS","New GU DUNS","Previous GU Name",'New GU Name'
]

display_columns1 = [
    "Enterprise ID", "Account Name", "Record Type ID", "Ultimate Parent Name",
    "Ultimate Parent Enterprise ID", "Billing Street","D&B Connect DUNS Number", "D&B Connect GU DUNS",
    "D&B Connect GU Name","D&B Connect Company Profile"
]

# Columns for the ticket grid
ticket_columns = [
    "TicketID", "D&B ProfileID", "Previous GU DUNS", "Previous GU Name",
    "New GU DUNS", "New GU Name", "Reason"
]

# Initialize session state for login
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Password hashing function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if not st.session_state.authenticated:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        hashed_pw = hash_password(password)
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed_pw))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.stop()
# -------------------------------
# Load data once authenticated
# -------------------------------
conn = get_connection()
ticket_df = pd.read_sql("SELECT * FROM ticket_table", conn)
current_df = pd.read_sql("SELECT * FROM current_accounts", conn)
future_df = pd.read_sql("SELECT * FROM future_accounts", conn)
conn.close()

# Initialize session state
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Full Table View"
if "selected_ticket" not in st.session_state:
    st.session_state.selected_ticket = None
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "filtered_reasons" not in st.session_state:
    st.session_state.filtered_reasons = []
if "all_reasons" not in st.session_state:
    st.session_state.all_reasons = ticket_df["Reason"].unique().tolist()

# Get sorted list of ticket IDs
ticket_ids = sorted(ticket_df["TicketID"].unique().tolist())

st.sidebar.markdown(f"👤 Logged in as: `{st.session_state.username}`")

# Sidebar navigation
view_mode = st.sidebar.radio(
    "Navigation",
    ["Full Table View", "Single Ticket View"],
    index=0 if st.session_state.view_mode == "Full Table View" else 1
)

# Update view mode if sidebar selection changes
if view_mode != st.session_state.view_mode:
    st.session_state.view_mode = view_mode
    st.rerun()

if st.session_state.view_mode == "Single Ticket View":
    # Apply reason filter to ticket IDs
    if st.session_state.filtered_reasons:
        filtered_ticket_ids = sorted(ticket_df[ticket_df["Reason"].isin(st.session_state.filtered_reasons)]["TicketID"].unique().tolist())
    else:
        filtered_ticket_ids = ticket_ids
    
    # If no tickets match the filter
    if not filtered_ticket_ids:
        st.warning("No tickets match the selected reasons. Redirecting to Full Table View.")
        st.session_state.view_mode = "Full Table View"
        st.rerun()
    
    # If no ticket selected, use first ticket from filtered list
    if st.session_state.selected_ticket in filtered_ticket_ids:
        ticket_id = st.session_state.selected_ticket
        st.session_state.current_index = filtered_ticket_ids.index(ticket_id)
    else:
        # If not in filtered list, reset to first valid ticket
        ticket_id = filtered_ticket_ids[0]
        st.session_state.selected_ticket = ticket_id
        st.session_state.current_index = 0

    
    ticket_id = st.session_state.selected_ticket
    reason_series = ticket_df[ticket_df['TicketID'] == ticket_id]['Reason']
    reason = reason_series.iloc[0] if not reason_series.empty else "N/A"

    # Reason filter menu
    st.sidebar.markdown("### Filter by Reason")
    selected_reasons = st.sidebar.multiselect(
        "Select reasons to filter tickets:",
        st.session_state.all_reasons,
        st.session_state.filtered_reasons,
        key="reason_filter"
    )
    
    # Apply filter button
    if st.sidebar.button("Apply Reason Filter"):
        st.session_state.filtered_reasons = selected_reasons
        # Reset to first ticket in filtered list
        st.session_state.selected_ticket = filtered_ticket_ids[0]
        st.session_state.current_index = 0
        st.rerun()
    
    # Clear filter button
    if st.sidebar.button("Clear Reason Filter"):
        st.session_state.filtered_reasons = []
        st.session_state.selected_ticket = filtered_ticket_ids[0] if filtered_ticket_ids else None
        st.session_state.current_index = 0
        st.rerun()

    # Navigation buttons
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 1, 7])
    
    # Previous button
    if col_nav1.button("⏮ Previous"):
        if st.session_state.current_index > 0:
            st.session_state.current_index -= 1
            st.session_state.selected_ticket = filtered_ticket_ids[st.session_state.current_index]
            st.rerun()
    
    # Next button
    if col_nav2.button("⏭ Next"):
        if st.session_state.current_index < len(filtered_ticket_ids) - 1:
            st.session_state.current_index += 1
            st.session_state.selected_ticket = filtered_ticket_ids[st.session_state.current_index]
            st.rerun()
    
    # Position indicator
    col_nav3.write(f"Ticket {st.session_state.current_index + 1} of {len(filtered_ticket_ids)}")
    
    # Filter status indicator
    if st.session_state.filtered_reasons:
        col_nav4.write(f"Filtered by: {', '.join(st.session_state.filtered_reasons)}")
    
    # Ticket info
    st.subheader(f"Ticket: {ticket_id}")
    st.subheader(f"Reason: {reason}")

    # Filter rows for the selected ticket
    
    current_row = current_df[current_df["TicketID"] == ticket_id][display_columns]
    future_row = future_df[future_df["TicketID"] == ticket_id][display_columns1]

    # Create two columns for side-by-side display
    col1, col2 = st.columns(2)
    
    # Custom CSS to increase dataframe height and adjust column widths
    st.markdown("""
        <style>
            .dataframe-container {
                height: 800px !important;
                overflow-y: auto !important;
            }
            .dataframe th:first-child {
                width: 30% !important;
                min-width: 200px !important;
            }
            .dataframe td:first-child {
                width: 30% !important;
                min-width: 200px !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Left column: Accounts linked to D&B Profile
    with col1:
        st.markdown("### Accounts linked to D&B Profile")
        transposed = current_row.transpose().reset_index()
        transposed.columns = ['Field'] + [str(i + 1) for i in range(transposed.shape[1] - 1)]
        st.dataframe(transposed, height=500, width=None, hide_index=True, use_container_width=True)
    
    # Right column: Accounts Linked to D&B GU Profile
    with col2:
        st.markdown("### Accounts Linked to D&B GU Profile")
        transposed1 = future_row.transpose().reset_index()
        transposed1.columns = ['Field'] + [str(i + 1) for i in range(transposed1.shape[1] - 1)]
        st.dataframe(transposed1, height=500, width=None, hide_index=True, use_container_width=True)

    def log_decision(ticket_id, status, approver):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE ticket_table
        SET "Status" = %s, "Approver" = %s
        WHERE "TicketID" = %s
    """, ("Approved" if status else "Denied", approver, ticket_id))
        conn.commit()
        cur.close()
        conn.close()

    col_a, col_b, col_c = st.columns([1, 1,1])

    if col_a.button("✅ Approve"):
        log_decision(ticket_id, True, st.session_state.username)
        st.success(f"Ticket: {ticket_id} approved.")
        st.session_state.current_index += 1
        st.session_state.selected_ticket = filtered_ticket_ids[st.session_state.current_index]
        st.rerun()

    if col_b.button("❌ Deny"):
        log_decision(ticket_id, False, st.session_state.username)
        st.warning(f"Ticket: {ticket_id} denied.")
        st.session_state.current_index += 1
        st.session_state.selected_ticket = filtered_ticket_ids[st.session_state.current_index]
        st.rerun()

    if col_c.button("← Back to Ticket List"):
            st.session_state.selected_ticket = None
            st.session_state.view_mode = "Full Table View"
            st.rerun()

else:
    st.subheader("All Tickets")

    # 1. Multiselect filter for Reason
    selected_reasons = st.multiselect(
        "Filter tickets by Reason",
        options=st.session_state.all_reasons,
        default=st.session_state.filtered_reasons
    )

    # 2. Filter dataframe by selected reasons
    if selected_reasons:
        filtered_tickets = ticket_df[ticket_df["Reason"].isin(selected_reasons)]
    else:
        filtered_tickets = ticket_df.copy()

    # 4. Prepare data for bar chart (counts per Reason)
    reason_counts = filtered_tickets["Reason"].value_counts()

    # 5. Display bar chart with Streamlit native API
    st.subheader("Tickets by Reason")
    st.bar_chart(reason_counts)

# 6. Ticket selector and row selection to view details
    selected_data = st.dataframe(
        filtered_tickets[ticket_columns],
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="ticket_selector_df"
    )

    if selected_data and selected_data.get("selection", {}).get("rows"):
        st.session_state.view_mode = "Single Ticket View"
        selected_index = selected_data["selection"]["rows"][0]
        selected_ticket_id = filtered_tickets.iloc[selected_index]["TicketID"]
        st.session_state.selected_ticket = selected_ticket_id
        st.rerun()
