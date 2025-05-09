import streamlit as st
from src.claim_validator import run_claim_validation, get_quotation_data

st.set_page_config(page_title="Claim Validator", page_icon="💼")
st.title("🧾 Insurance Claim Validator")

# Sidebar: claim form
st.sidebar.header("📝 Claim Information")
claim_id = st.sidebar.text_input("Claim ID", value="1234")
member_id = st.sidebar.text_input("Member ID", value="A456")
member_name = st.sidebar.text_input("Member Name", value="Sameeh")
class_ = st.sidebar.selectbox("Class", ["VIP", "A", "B+", "CR"], index=0)
diagnosis = st.sidebar.text_input("Diagnosis", value="dental")
amount = st.sidebar.number_input("Claim Amount", value=1000)
date = st.sidebar.text_input("Date", value="01-05-2024")

# Construct claim
claim = {
    "claim_id": claim_id,
    "company_id": "company_X",
    "amount": amount,
    "member_id": member_id,
    "member_name": member_name,
    "class": class_,
    "diagnosis": diagnosis,
    "date": date,
}

# Submit button
if st.button("✅ Validate Claim"):
    with st.spinner("Evaluating claim..."):
        quotation_data = get_quotation_data(class_)
        result = run_claim_validation(claim, quotation_data)
        msg = result['messages'][-1]

        st.subheader("🧠 Decision:")
        st.markdown(f"**{msg.content}**")

        st.subheader("🧾 Justification:")
        st.write(msg.additional_kwargs['justification'])