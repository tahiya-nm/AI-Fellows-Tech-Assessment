import re
import asyncio
import streamlit as st

from core_agent import execute_agent_run, QueryPayload

st.set_page_config(
    page_title="Antenatal Care Assistant", 
    page_icon="🤰", 
    layout="centered"
)

# ==========================================
# 1. STATE INITIALIZATION & MODE TOGGLE
# ==========================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "professional_mode" not in st.session_state:
    st.session_state.professional_mode = False

def toggle_professional_mode():
    """Flips the view between Patient and Clinician modes."""
    st.session_state.professional_mode = not st.session_state.professional_mode

# ==========================================
# 2. DYNAMIC STYLING & UI HEADER
# ==========================================
# Base CSS for right-aligning user messages
custom_css = """
<style>
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        flex-direction: row-reverse;
        text-align: right;
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# Top Right Button Layout
col_title, col_button = st.columns([3, 1], vertical_alignment="bottom")
with col_title:
    st.title("Antenatal Care Assistant", anchor=False)
with col_button:
    button_text = "Exit Clinician Mode" if st.session_state.professional_mode else "⚕️ Clinician Access"
    st.button(button_text, on_click=toggle_professional_mode, use_container_width=True)

# Show instructional banner or standard subheader
if st.session_state.professional_mode:
    st.info("⚕️ **CLINICIAN MODE ACTIVE**\n\nReview the patient's chat history below. Any message you type will bypass the AI and be delivered directly to the patient as a verified clinical response.")
else:
    st.markdown("Ask me questions about your pregnancy, nutrition, and antenatal care scheduling.")

# ==========================================
# 3. CUSTOM RENDERER (CITATION & PRO TAGS)
# ==========================================
def format_assistant_content(content: str, is_professional: bool = False):
    """Renders either a human professional badge or parses AI citations."""
    
    # If it's a human professional, render a distinct badge and the text
    if is_professional:
        pro_badge = """
        <div style='color: #0c5460; background-color: #d1ecf1; padding: 4px 12px; 
                    border-radius: 4px; font-weight: bold; margin-bottom: 8px; 
                    font-size: 0.85rem; display: inline-block;'>
            ⚕️ Verified Clinician Response
        </div>
        """
        st.markdown(pro_badge, unsafe_allow_html=True)
        st.markdown(content)
        return

    # Normal AI formatting
    citation_match = re.search(r'\[SOURCE:(.*?)\]', content, re.IGNORECASE)
    
    if citation_match:
        main_text = content[:citation_match.start()].strip()
        source_text = citation_match.group(1).strip()
        
        url_match = re.search(r'(.*?)\s*\((https?://[^\)]+)\)', source_text)
        
        if url_match:
            org_name = url_match.group(1).strip()
            source_url = url_match.group(2).strip()
            display_source = f"<a href='{source_url}' target='_blank' style='color: #1f77b4; text-decoration: underline; font-weight: 500;'>{org_name}</a>"
        else:
            display_source = source_text
        
        st.markdown(main_text)
        
        html_bubble = f"""
        <div style="background-color: #e0e5eb; color: #31333F; padding: 4px 12px; 
                    border-radius: 16px; font-size: 0.8rem; display: inline-block; 
                    margin-top: 8px; border: 1px solid #c4c9d0;">
            🔍 Source: {display_source}
        </div>
        """
        st.markdown(html_bubble, unsafe_allow_html=True)
    else:
        st.markdown(content)

# ==========================================
# 4. INITIAL LOAD SCREEN (LANDING PAGE)
# ==========================================
SUGGESTIONS = {
    "📅 When should I have my first visit?": "When should I have my first doctor visit?",
    "🛏️ Sleep positions at 8 months": "Is it okay to sleep on my back at 8 months?",
    "💉 Required vaccines": "Which vaccines do I need while pregnant?",
}

user_just_asked_initial = "initial_question" in st.session_state and st.session_state.initial_question
user_just_clicked_suggestion = "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
user_first_interaction = user_just_asked_initial or user_just_clicked_suggestion
has_message_history = len(st.session_state.chat_history) > 0

# Only show landing page if NO history, NO new interaction, AND NOT in professional mode
if not user_first_interaction and not has_message_history and not st.session_state.professional_mode:
    with st.container():
        st.chat_input("Type your question here...", key="initial_question")
        st.pills(
            label="Examples",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )
    st.stop()

# ==========================================
# 5. MAIN CHAT EXECUTION LOOP
# ==========================================
input_placeholder = "Type clinical response..." if st.session_state.professional_mode else "Ask a follow-up..."
user_prompt = st.chat_input(input_placeholder)

# Handle the transition from the landing page correctly
if not user_prompt and not st.session_state.professional_mode:
    if user_just_asked_initial:
        user_prompt = st.session_state.initial_question
    elif user_just_clicked_suggestion:
        user_prompt = SUGGESTIONS[st.session_state.selected_suggestion]

# Render all previous messages
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            format_assistant_content(message["content"], message.get("is_professional", False))
        else:
            st.markdown(message["content"])

if user_prompt:
    if st.session_state.professional_mode:
        # Professional is typing ON BEHALF of the assistant
        with st.chat_message("assistant"):
            format_assistant_content(user_prompt, is_professional=True)
            
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": user_prompt, 
            "is_professional": True
        })
        st.rerun()
        
    else:
        # Standard Patient Flow
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving information..."):
                payload = QueryPayload(
                    current_prompt=user_prompt,
                    chat_history=st.session_state.chat_history 
                )
                try:
                    result_dict = asyncio.run(execute_agent_run(payload))
                    agent_response = result_dict.get("response", "Error: No response generated.")
                    
                    # Scrub OpenAI markers
                    agent_response = re.sub(r'.*?', '', agent_response)
                    agent_response = re.sub(r'【.*?】', '', agent_response)
                except Exception as error:
                    agent_response = f"System Error: {error}"

            # Format and render AI response
            format_assistant_content(agent_response, is_professional=False)

        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": agent_response, 
            "is_professional": False
        })