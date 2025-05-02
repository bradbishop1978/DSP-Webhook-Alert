import streamlit as st
import pandas as pd
import requests
import io
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

# Use the GitHub raw content URL instead of the blob URL
# This is the correct way to access raw files from GitHub
CSV_URL = "https://raw.githubusercontent.com/bradbishop1978/DSP-Webhook-Alert/main/dsp_alert_report.csv"
REFRESH_INTERVAL = 10 * 60  # 10 minutes in seconds
STATUS_OPTIONS = ["", "Dormant", "Inactive", "Endorsed", "Fixed"]
PERSISTENCE_FILE = "status_persistence.json"

# Function to load the CSV data with debugging
@st.cache_data(ttl=REFRESH_INTERVAL)
def load_data():
    try:
        # Download the file using requests
        response = requests.get(CSV_URL)
        response.raise_for_status()
        
        # Read the CSV from the response content
        df = pd.read_csv(io.StringIO(response.text))
        
        # Debug: Print column names and row count
        st.sidebar.write(f"Columns in CSV: {', '.join(df.columns.tolist())}")
        st.sidebar.write(f"Number of rows: {len(df)}")
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

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

# Check if data is empty
if data.empty:
    st.error("Failed to load data. Please check the CSV URL and format.")
    st.stop()

# Display last refresh time
st.sidebar.write(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.write("Data refreshes automatically every 10 minutes")

# Add a manual refresh button
if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()
    st.rerun()

# Create the dashboard
st.write(f"Total stores: {len(data)}")

# Create a container for the table
table_container = st.container()

# Determine the correct column names
# Let's check if we can find the store ID column
id_column = None
name_column = None
company_column = None

# Try to find columns by common patterns
for col in data.columns:
    col_lower = col.lower()
    if 'id' in col_lower and ('store' in col_lower or 'location' in col_lower):
        id_column = col
    elif 'name' in col_lower and ('store' in col_lower or 'location' in col_lower):
        name_column = col
    elif 'company' in col_lower or 'business' in col_lower:
        company_column = col

# If we couldn't find the columns, use the first column as ID and second as name
if id_column is None and len(data.columns) > 0:
    id_column = data.columns[0]
    st.warning(f"Could not find a store ID column. Using '{id_column}' instead.")

if name_column is None and len(data.columns) > 1:
    name_column = data.columns[1]
    st.warning(f"Could not find a store name column. Using '{name_column}' instead.")

if company_column is None and len(data.columns) > 2:
    company_column = data.columns[2]
    st.warning(f"Could not find a company name column. Using '{company_column}' instead.")

# Create a form for the status dropdowns
with st.form("store_status_form"):
    # Display the data with clickable store names and status dropdowns
    for index, row in data.iterrows():
        # Get the store ID (or use index if not found)
        store_id = str(row[id_column]) if id_column in data.columns else str(index)
        
        # Create a unique key for each store based on store_id
        if store_id not in st.session_state.status_data:
            st.session_state.status_data[store_id] = ""
        
        # Create columns for each row
        col1, col2, col3, col4 = st.columns([2, 3, 3, 2])
        
        with col1:
            st.write(f"{index + 1}. ID: {store_id[:8]}...")
        
        with col2:
            # Display company name if available
            if company_column and company_column in data.columns:
                st.write(f"**Company**: {row[company_column]}")
            else:
                st.write("**Company**: N/A")
        
        with col3:
            # Make store name clickable
            store_name = row[name_column] if name_column in data.columns else f"Store {index}"
            store_url = f"https://www.lulastoremanager.com/stores/{store_id}"
            st.markdown(f"[{store_name}]({store_url})")
        
        with col4:
            # Status dropdown
            selected_status = st.selectbox(
                "Status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(st.session_state.status_data[store_id]) if st.session_state.status_data[store_id] in STATUS_OPTIONS else 0,
                key=f"status_{store_id}"
            )
            # Update session state when dropdown changes
            st.session_state.status_data[store_id] = selected_status
        
        # Add a separator between rows
        st.markdown("---")
    
    # Submit button to save status changes
    submitted = st.form_submit_button("Save Status Changes")
    if submitted:
        save_status_data(st.session_state.status_data)
        st.success("Status changes saved successfully!")

# Auto-refresh functionality using a safer approach
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = time.time()

# Check if it's time to refresh
current_time = time.time()
if current_time - st.session_state.last_refresh_time > REFRESH_INTERVAL:
    st.session_state.last_refresh_time = current_time
    st.cache_data.clear()
    st.rerun()

# Add filters in the sidebar
st.sidebar.header("Filters")

# Filter by status
status_filter = st.sidebar.multiselect(
    "Filter by Status",
    options=STATUS_OPTIONS[1:],  # Exclude empty option
)

# Apply filters if any are selected
if status_filter:
    filtered_indices = [i for i, row in data.iterrows() 
                       if st.session_state.status_data.get(str(row[id_column]) if id_column in data.columns else str(i), "") in status_filter]
    
    if filtered_indices:
        filtered_data = data.iloc[filtered_indices]
        st.sidebar.write(f"Showing {len(filtered_data)} of {len(data)} stores")
        
        # Display filtered data
        st.subheader("Filtered Stores")
        for index, row in filtered_data.iterrows():
            store_id = str(row[id_column]) if id_column in data.columns else str(index)
            store_name = row[name_column] if name_column in data.columns else f"Store {index}"
            st.write(f"{store_name} - Status: {st.session_state.status_data.get(store_id, '')}")
