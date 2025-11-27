import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ### INJECTED_CODE ####
# ### QUERY DATA FUNCTION ####
import os
import time

import httpx
import pandas as pd


def query_data(query: str) -> pd.DataFrame:
    branch_id = os.environ.get('BRANCH_ID')
    workspace_id = os.environ.get('WORKSPACE_ID')
    token = os.environ.get('KBC_TOKEN')
    kbc_url = os.environ.get('KBC_URL')

    if not branch_id or not workspace_id or not token or not kbc_url:
        raise RuntimeError('Missing required environment variables: BRANCH_ID, WORKSPACE_ID, KBC_TOKEN, KBC_URL.')

    query_service_url = kbc_url.replace('connection.', 'query.', 1).rstrip('/') + '/api/v1'
    headers = {
        'X-StorageAPI-Token': token,
        'Accept': 'application/json',
    }

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=None)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    with httpx.Client(timeout=timeout, limits=limits) as client:
        response = client.post(
            f'{query_service_url}/branches/{branch_id}/workspaces/{workspace_id}/queries',
            json={'statements': [query]},
            headers=headers,
        )
        response.raise_for_status()
        submission = response.json()
        job_id = submission.get('queryJobId')
        if not job_id:
            raise RuntimeError('Query Service did not return a job identifier.')

        start_ts = time.monotonic()
        while True:
            status_response = client.get(
                f'{query_service_url}/queries/{job_id}',
                headers=headers,
            )
            status_response.raise_for_status()
            job_info = status_response.json()
            status = job_info.get('status')
            if status in {'completed', 'failed', 'canceled'}:
                break
            if time.monotonic() - start_ts > 300:  # 5 minutes
                raise TimeoutError(f'Timed out waiting for query "{job_id}" to finish.')
            time.sleep(1)

        statements = job_info.get('statements') or []
        if not statements:
            raise RuntimeError('Query Service returned no statements for the executed query.')
        statement_id = statements[0]['id']

        results_response = client.get(
            f'{query_service_url}/queries/{job_id}/{statement_id}/results',
            headers=headers,
        )
        results_response.raise_for_status()
        results = results_response.json()

        if results.get('status') != 'completed':
            raise ValueError(f'Error when executing query "{query}": {results.get("message")}.')

        columns = [col['name'] for col in results.get('columns', [])]
        data_rows = [{col_name: value for col_name, value in zip(columns, row)} for row in results.get('data', [])]
        return pd.DataFrame(data_rows)


# ### END_OF_INJECTED_CODE ####


st.set_page_config(page_title="Conversion Funnel Dashboard", layout="wide")

st.title("🛒 Amplitude Conversion Funnel Dashboard")
st.markdown("### View Product → Complete Purchase Analysis")

# Fetch event-level funnel data
funnel_query = """
SELECT 
  "event_type",
  COUNT(*) as event_count
FROM "SAPI_10504"."out.c-amplitude"."events"
WHERE "event_type" IN ('View Product', 'Add to Cart', 'Start Checkout', 'Complete Purchase')
GROUP BY "event_type"
ORDER BY 
  CASE "event_type"
    WHEN 'View Product' THEN 1
    WHEN 'Add to Cart' THEN 2
    WHEN 'Start Checkout' THEN 3
    WHEN 'Complete Purchase' THEN 4
  END
"""

funnel_df = query_data(funnel_query)

# Fetch user-level funnel data
user_funnel_query = """
WITH user_events AS (
  SELECT 
    "user_id",
    MAX(CASE WHEN "event_type" = 'View Product' THEN 1 ELSE 0 END) as viewed_product,
    MAX(CASE WHEN "event_type" = 'Add to Cart' THEN 1 ELSE 0 END) as added_to_cart,
    MAX(CASE WHEN "event_type" = 'Start Checkout' THEN 1 ELSE 0 END) as started_checkout,
    MAX(CASE WHEN "event_type" = 'Complete Purchase' THEN 1 ELSE 0 END) as completed_purchase
  FROM "SAPI_10504"."out.c-amplitude"."events"
  GROUP BY "user_id"
)
SELECT 
  SUM(viewed_product) as users_viewed_product,
  SUM(added_to_cart) as users_added_to_cart,
  SUM(started_checkout) as users_started_checkout,
  SUM(completed_purchase) as users_completed_purchase
FROM user_events
"""

user_funnel_df = query_data(user_funnel_query)

# Fix column name case sensitivity - Snowflake returns uppercase by default
funnel_df.columns = funnel_df.columns.str.lower()
user_funnel_df.columns = user_funnel_df.columns.str.lower()

# Convert to integers - query returns strings
events_list = [int(x) for x in funnel_df['event_count'].tolist()]
stages = ['View Product', 'Add to Cart', 'Start Checkout', 'Complete Purchase']

# Create two columns for metrics
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📊 Event-Level Metrics")
    st.metric("Total Product Views", f"{events_list[0]:,}")
    st.metric("Total Add to Cart", f"{events_list[1]:,}", 
              f"{(events_list[1]/events_list[0]*100):.1f}% of views")
    st.metric("Total Checkouts Started", f"{events_list[2]:,}", 
              f"{(events_list[2]/events_list[1]*100):.1f}% of carts")
    st.metric("Total Purchases", f"{events_list[3]:,}", 
              f"{(events_list[3]/events_list[2]*100):.1f}% of checkouts")

with col2:
    st.markdown("#### 👥 User-Level Metrics")
    users_viewed = int(user_funnel_df['users_viewed_product'].iloc[0])
    users_cart = int(user_funnel_df['users_added_to_cart'].iloc[0])
    users_checkout = int(user_funnel_df['users_started_checkout'].iloc[0])
    users_purchase = int(user_funnel_df['users_completed_purchase'].iloc[0])
    
    st.metric("Users Viewed Products", f"{users_viewed:,}")
    st.metric("Users Added to Cart", f"{users_cart:,}", 
              f"{(users_cart/users_viewed*100):.1f}% conversion")
    st.metric("Users Started Checkout", f"{users_checkout:,}", 
              f"{(users_checkout/users_cart*100):.1f}% conversion")
    st.metric("Users Completed Purchase", f"{users_purchase:,}", 
              f"{(users_purchase/users_checkout*100):.1f}% conversion")

# Overall conversion rate
st.markdown("---")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("📈 Overall Event Conversion Rate", f"{(events_list[3]/events_list[0]*100):.2f}%")
with col_b:
    st.metric("📈 Overall User Conversion Rate", f"{(users_purchase/users_viewed*100):.2f}%")
with col_c:
    st.metric("🔄 Avg Events per Converting User", f"{(events_list[3]/users_purchase):.1f}")

st.markdown("---")

# Funnel visualization
st.markdown("### 📉 Funnel Visualization")

tab1, tab2 = st.tabs(["Event-Level Funnel", "User-Level Funnel"])

with tab1:
    # Event-level funnel chart
    fig_event = go.Figure(go.Funnel(
        y=stages,
        x=events_list,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]),
        connector=dict(line=dict(color="royalblue", dash="dot", width=3))
    ))
    
    fig_event.update_layout(
        title="Event-Level Conversion Funnel",
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig_event, use_container_width=True)
    
    # Event-level conversion table
    conversion_data = []
    for i, (stage, count) in enumerate(zip(stages, events_list)):
        if i == 0:
            conv_rate = 100.0
            drop_off = 0
        else:
            conv_rate = (count / events_list[i-1]) * 100
            drop_off = events_list[i-1] - count
        
        conversion_data.append({
            'Stage': stage,
            'Events': f"{count:,}",
            'Conversion from Previous': f"{conv_rate:.2f}%",
            'Drop-off': f"{drop_off:,}" if i > 0 else "-"
        })
    
    st.dataframe(pd.DataFrame(conversion_data), use_container_width=True, hide_index=True)

with tab2:
    # User-level funnel chart
    user_counts = [users_viewed, users_cart, users_checkout, users_purchase]
    
    fig_user = go.Figure(go.Funnel(
        y=stages,
        x=user_counts,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=["#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]),
        connector=dict(line=dict(color="purple", dash="dot", width=3))
    ))
    
    fig_user.update_layout(
        title="User-Level Conversion Funnel",
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig_user, use_container_width=True)
    
    # User-level conversion table
    user_conversion_data = []
    for i, (stage, count) in enumerate(zip(stages, user_counts)):
        if i == 0:
            conv_rate = 100.0
            drop_off = 0
        else:
            conv_rate = (count / user_counts[i-1]) * 100
            drop_off = user_counts[i-1] - count
        
        user_conversion_data.append({
            'Stage': stage,
            'Unique Users': f"{count:,}",
            'Conversion from Previous': f"{conv_rate:.2f}%",
            'Drop-off': f"{drop_off:,}" if i > 0 else "-"
        })
    
    st.dataframe(pd.DataFrame(user_conversion_data), use_container_width=True, hide_index=True)

# Additional insights
st.markdown("---")
st.markdown("### 💡 Key Insights")

col1, col2 = st.columns(2)

with col1:
    st.info(f"""
    **Largest Drop-off Point (Events)**  
    From View Product to Add to Cart: {events_list[0] - events_list[1]:,} events lost ({((events_list[0] - events_list[1])/events_list[0]*100):.1f}%)
    """)

with col2:
    st.success(f"""
    **Best Performing Stage**  
    Checkout Completion Rate: {(events_list[3]/events_list[2]*100):.1f}% of users who start checkout complete their purchase
    """)

# Footer
st.markdown("---")
st.caption("Data refreshes when the dashboard is reloaded. Based on Amplitude events data.")
