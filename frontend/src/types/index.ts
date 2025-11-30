// Re-export chat types
export type {
  Message,
  ToolUse,
  ToolUseEvent,
  TextDeltaEvent,
  MessageCompleteEvent,
  PreviewUpdateEvent,
  ErrorEvent,
  StatusEvent,
  WebSocketEvent,
  ChatState,
  ChatMessage,
} from './chat';

export interface LogEntry {
  id: string;
  timestamp: number;
  message: string;
  level: 'info' | 'success' | 'error' | 'stream' | 'debug';
}

export interface SandboxState {
  status: 'idle' | 'creating' | 'installing' | 'uploading' | 'starting' | 'running' | 'error' | 'stopped';
  sandboxId?: string;
  publicUrl?: string;
  error?: string;
}

export interface LaunchConfig {
  code: string;
  template?: string;
  port: number;
  envVars?: Record<string, string>;
  packages?: string[];
}

export interface ScriptFile {
  name: string;
  path: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  preInstalled: string[];
}

export const TEMPLATES: Template[] = [
  {
    id: '',
    name: 'Default (No Template)',
    description: 'Installs dependencies at runtime (~12s)',
    preInstalled: [],
  },
  {
    id: 'keboola-streamlit-dev',
    name: 'Keboola Streamlit',
    description: 'Streamlit + Keboola SDK (~4s)',
    preInstalled: ['streamlit', 'pandas', 'kbcstorage', 'plotly'],
  },
];

export const EXAMPLE_SCRIPTS: Record<string, string> = {
  'Hello World': `import streamlit as st

st.set_page_config(page_title="Hello E2B!", page_icon="🚀")

st.title("🚀 Hello from E2B Sandbox!")
st.write("This Streamlit app is running in an isolated E2B sandbox.")

name = st.text_input("What's your name?", "World")
st.success(f"Hello, {name}! 👋")

st.balloons()
`,

  'Data Dashboard': `import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Data Dashboard", page_icon="📊", layout="wide")

st.title("📊 Interactive Data Dashboard")

# Generate sample data
@st.cache_data
def generate_data():
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'date': dates,
        'sales': np.random.randint(100, 1000, 100),
        'visitors': np.random.randint(500, 5000, 100),
        'conversion': np.random.uniform(0.01, 0.1, 100)
    })

data = generate_data()

# Metrics row
col1, col2, col3 = st.columns(3)
total_sales = data['sales'].sum()
col1.metric("Total Sales", "$" + f"{total_sales:,}", "+12%")
col2.metric("Total Visitors", f"{data['visitors'].sum():,}", "+8%")
col3.metric("Avg Conversion", f"{data['conversion'].mean():.2%}", "+2%")

# Charts
st.subheader("Sales Over Time")
fig = px.line(data, x='date', y='sales', title='Daily Sales')
fig.update_layout(template='plotly_dark')
st.plotly_chart(fig, use_container_width=True)

st.subheader("Raw Data")
st.dataframe(data, use_container_width=True)
`,

  'Interactive Form': `import streamlit as st

st.set_page_config(page_title="Contact Form", page_icon="📝")

st.title("📝 Contact Form Demo")

with st.form("contact_form"):
    st.subheader("Get in Touch")

    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name")
    with col2:
        last_name = st.text_input("Last Name")

    email = st.text_input("Email")
    subject = st.selectbox("Subject", ["General Inquiry", "Support", "Feedback", "Partnership"])
    message = st.text_area("Message", height=150)
    priority = st.slider("Priority", 1, 5, 3)

    submitted = st.form_submit_button("Send Message", type="primary")

    if submitted:
        if first_name and email and message:
            st.success("✅ Message sent successfully!")
            st.json({
                "name": f"{first_name} {last_name}",
                "email": email,
                "subject": subject,
                "priority": priority
            })
        else:
            st.error("Please fill in all required fields")
`,
};
