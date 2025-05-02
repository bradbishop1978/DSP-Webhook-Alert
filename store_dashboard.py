import streamlit as st
import pandas as pd
import time
import json
import os
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Store Management Dashboard",
    page_icon="🏪",
    layout="wide"
)

# Constants
CSV_URL = "https://github.com/bradbishop1978/DSP-Webhook-Alert/blob/main/dsp_alert_report.csv"
REFRESH_INTERVAL = 10 * 60  # 10 minutes in seconds
STATUS_OPTIONS = ["", "Dormant", "Inactive", "Endorsed", "Fixed"]
PERSISTENCE_FILE = "status_persistence.json"

# Function to load the CSV data
@st.cache_data(ttl=REFRESH_INTERVAL)
def load_data():
    return pd.read_csv(CSV_URL)

# Function to load persisted status data
def load_status_data():
    if os.path.exists(PERSISTENCE_FILE):
        with open(PERSISTENCE_FILE, 'r') as f:
            return json.load(f)
    return {}

# Function to save persisted status data
def save_status_data(status_data):
    with open(PERSISTENCE_FILE, 'w') as f:
        json.dump(status_data, f)

# Initialize session state for status tracking if not already done
if 'status_data' not in st.session_state:
    st.session_state.status_data = load_status_data()

# Main dashboard
st.title("Store Management Dashboard")

# Load the data
data = load_data()

# Display last refresh time
st.sidebar.write(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.write("Data refreshes automatically every 10 minutes")

# Add a manual refresh button
if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()
    st.experimental_rerun()

# Create the dashboard
st.write(f"Total stores: {len(data)}")

# Create a container for the table
table_container = st.container()

# Create a form for the status dropdowns
with st.form("store_status_form"):
    # Display the data with clickable store names and status dropdowns
    for index, row in data.iterrows():
        store_id = row['store_id']
        
        # Create a unique key for each store based on store_id
        if store_id not in st.session_state.status_data:
            st.session_state.status_data[store_id] = ""
        
        # Create columns for each row
        col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 3, 2, 2, 2])
        
        with col1:
            st.write(f"{index + 1}. ID: {store_id[:8]}...")
        
        with col2:
            st.write(f"**Company**: {row['company_name']}")
        
        with col3:
            # Make store name clickable
            store_url = f"https://www.lulastoremanager.com/stores/{store_id}"
            st.markdown(f"[{row['store_name']}]({store_url})")
        
        with col4:
            # Display inactive delivery services
            st.write(f"Inactive: {row['inactive_dsps']}")
        
        with col5:
            # Status dropdown
            selected_status = st.selectbox(
                "Status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(st.session_state.status_data[store_id]) if st.session_state.status_data[store_id] in STATUS_OPTIONS else 0,
                key=f"status_{store_id}"
            )
            # Update session state when dropdown changes
            st.session_state.status_data[store_id] = selected_status
        
        with col6:
            # Display the status since dates
            status_info = []
            if row['ubereats_status'] == 'Inactive':
                status_info.append(f"UE: {row['ubereats_since']}")
            if row['doordash_status'] == 'Inactive':
                status_info.append(f"DD: {row['doordash_since']}")
            if row['grubhub_status'] == 'Inactive':
                status_info.append(f"GH: {row['grubhub_since']}")
            st.write("<br>".join(status_info), unsafe_allow_html=True)
        
        # Add a separator between rows
        st.markdown("---")
    
    # Submit button to save status changes
    submitted = st.form_submit_button("Save Status Changes")
    if submitted:
        save_status_data(st.session_state.status_data)
        st.success("Status changes saved successfully!")

# Auto-refresh functionality
def auto_refresh():
    time.sleep(REFRESH_INTERVAL)
    st.experimental_rerun()

# Start the auto-refresh in a separate thread
if not st.session_state.get('auto_refresh_started', False):
    st.session_state.auto_refresh_started = True
    st.write("Auto-refresh is active. Dashboard will update every 10 minutes.")

# Add filters in the sidebar
st.sidebar.header("Filters")

# Filter by status
status_filter = st.sidebar.multiselect(
    "Filter by Status",
    options=STATUS_OPTIONS[1:],  # Exclude empty option
)

# Filter by delivery service status
delivery_filter = st.sidebar.multiselect(
    "Filter by Delivery Service Status",
    options=["UberEats Inactive", "DoorDash Inactive", "GrubHub Inactive"]
)

# Apply filters if any are selected
if status_filter or delivery_filter:
    filtered_data = data.copy()
    
    # Apply status filter
    if status_filter:
        filtered_indices = [i for i, row in data.iterrows() 
                           if st.session_state.status_data.get(row['store_id'], "") in status_filter]
        filtered_data = filtered_data.iloc[filtered_indices]
    
    # Apply delivery service filter
    if "UberEats Inactive" in delivery_filter:
        filtered_data = filtered_data[filtered_data['ubereats_status'] == 'Inactive']
    if "DoorDash Inactive" in delivery_filter:
        filtered_data = filtered_data[filtered_data['doordash_status'] == 'Inactive']
    if "GrubHub Inactive" in delivery_filter:
        filtered_data = filtered_data[filtered_data['grubhub_status'] == 'Inactive']
    
    # Show filtered data count
    st.sidebar.write(f"Showing {len(filtered_data)} of {len(data)} stores")
