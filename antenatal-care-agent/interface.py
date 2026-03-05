import re
import asyncio
import streamlit as st

# Import backend logic
from core_agent import execute_agent_run, QueryPayload

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Antenatal Care Assistant", 
    page_icon="🤰", 
    layout="centered"
)

# Custom CSS to right-align the user's chat bubbles
st.markdown(
    """
    <style>
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            flex-direction: row-reverse;
            text-align: right;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# 2. CUSTOM RENDERER (CITATION PARSING)
# ==========================================
def render_chat_message(role: str, content: str):
    """Parses citations from the agent and renders them as custom HTML bubbles."""
    
    if role == "assistant":
        # Search for our strict citation format: [SOURCE: ...]
        citation_match = re.search(r'\[SOURCE:(.*?)\]', content, re.IGNORECASE)
        
        if citation_match:
            # Separate the main conversational text from the citation
            main_text = content[:citation_match.start()].strip()
            source_text = citation_match.group(1).strip()
            
            # Check if the citation contains a URL: "Name (https://url)"
            url_match = re.search(r'(.*?)\s*\((https?://[^\)]+)\)', source_text)
            
            if url_match:
                org_name = url_match.group(1).strip()
                source_url = url_match.group(2).strip()
                display_source = f"<a href='{source_url}' target='_blank' style='color: #1f77b4; text-decoration: underline; font-weight: 500;'>{org_name}</a>"
            else:
                display_source = source_text
            
            with st.chat_message("assistant"):
                st.markdown(main_text)
                
                # Render the pill-shaped citation bubble
                html_bubble = f"""
                <div style="background-color: #e0e5eb; color: #31333F; padding: 4px 12px; 
                            border-radius: 16px; font-size: 0.8rem; display: inline-block; 
                            margin-top: 8px; border: 1px solid #c4c9d0;">
                    🔍 Source: {display_source}
                </div>
                """
                st.markdown(html_bubble, unsafe_allow_html=True)
        else:
            # Fallback if the agent misses the formatting instruction
            with st.chat_message("assistant"):
                st.markdown(content)
    else:
        # Standard rendering for user messages
        with st.chat_message("user"):
            st.markdown(content)


# ==========================================
# 3. STATE INITIALIZATION
# ==========================================
st.title("Antenatal Care Assistant")
st.markdown("Ask me questions about your pregnancy, nutrition, and antenatal care scheduling.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ==========================================
# 4. MAIN CHAT EXECUTION LOOP
# ==========================================
# Render all previous messages
for message in st.session_state.chat_history:
    render_chat_message(message["role"], message["content"])

# Await new user input
user_prompt = st.chat_input("Type your question here...")

if user_prompt:
    # 1. Save and render the user's prompt
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    render_chat_message("user", user_prompt)

    # 2. Trigger the backend agent with a loading spinner
    with st.chat_message("assistant"):
        with st.spinner("Retrieving ANC guidelines..."):
            
            # Construct the payload (excluding the current prompt from the history array)
            payload = QueryPayload(
                current_prompt=user_prompt,
                chat_history=st.session_state.chat_history[:-1] 
            )
            
            # Execute the asynchronous agent call
            try:
                result_dict = asyncio.run(execute_agent_run(payload))
                agent_response = result_dict.get("response", "Error: No response generated.")
            except Exception as error:
                agent_response = f"System Error: {error}"

        # 3. Render the parsed response
        render_chat_message("assistant", agent_response)

    # 4. Save the agent's response to history to maintain context
    st.session_state.chat_history.append({"role": "assistant", "content": agent_response})