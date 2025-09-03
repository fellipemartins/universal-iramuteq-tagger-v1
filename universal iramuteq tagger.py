import streamlit as st
import pandas as pd
import openai
import os
import time
from rapidfuzz import fuzz
from io import BytesIO

# Configure page
st.set_page_config(
    page_title="Universal Iramuteq Tagger",
    page_icon="📚",
    layout="wide"
)


# Load custom CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_openai_api_key():
    """
    Retrieve the OpenAI API key in the following order:
    1. From a local file (apikeys.py)
    2. From Streamlit secrets
    3. From user input
    """
    # Check local file (apikeys.py)
    try:
        import apikeys
        if hasattr(apikeys, "openai"):
            st.info("OpenAI API key loaded from local file (apikeys.py).")
            return apikeys.openai
    except ImportError:
        pass

    # Check Streamlit secrets
    try:
        if "openai_api_key" in st.secrets:
            st.info("OpenAI API key loaded from Streamlit secrets.")
            return st.secrets["openai_api_key"]
    except FileNotFoundError:
        pass
    except Exception as e:
        st.warning(f"Error reading secrets: {str(e)}")

    return None

# ------------------
# Helper Functions
# ------------------

def validate_excel_file(df):
    """Validate the uploaded Excel file structure."""
    required_columns = ['paper title', 'publication year', 'journal', 'abstract']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    return True

def generate_py_tag(year):
    """Generate publication year tag."""
    try:
        return f"*py_{int(year)}"
    except (ValueError, TypeError):
        st.warning(f"Invalid year format: {year}")
        return "*py_unknown"

def generate_jo_tag(journal):
    """Generate journal tag."""
    if not isinstance(journal, str):
        return "*jo_unknown"
    words = journal.strip().split()
    return "*jo_" + ''.join(word[0].lower() for word in words if word)

def generate_heading(row, custom_results):
    """Generate the complete heading with all tags."""
    heading = generate_py_tag(row['publication year']) + " " + generate_jo_tag(row['journal'])
    for res in custom_results:
        if res["value"]:
            heading += f" *{res['tag'].lower()}_{res['value'].lower()}"
    return heading

def classify_custom_tag(objective, tag, subtags, definition, abstract, openai_client):
    """Classify abstract using OpenAI API."""
    if not abstract or not isinstance(abstract, str):
        return ""

    # Convert tag and subtags to lowercase
    tag = tag.lower()
    subtags = [s.lower() for s in subtags]

    prompt = (
        f"Task: Classify the following academic abstract into one of these categories for tag '{tag}'.\n"
        f"Context: The study objective is '{objective}'\n"
        f"Tag definition: {definition}\n"
        f"Available categories: {', '.join(subtags)}\n"
        f"Abstract: {abstract}\n\n"
        f"Rules:\n"
        "1. Return ONLY the category name in lowercase\n"
        "2. If no category fits, return 'none'\n"
        "3. Be precise and consistent\n"
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Latest model as per blueprint
            messages=[
                {"role": "system", "content": "You are a precise academic text classifier."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0,
            response_format={"type": "text"}
        )
        result = response.choices[0].message.content.strip().lower()
        return result if result in subtags else ""
    except Exception as e:
        st.error(f"Classification error for tag '{tag}': {str(e)}")
        time.sleep(1)  # Rate limiting protection
        return ""

# ------------------
# Main Application
# ------------------

def main():
    st.title("🏷️ Universal Iramuteq Tagger")
    st.markdown("""
    This application helps classify academic papers' abstracts using custom tags and OpenAI's
    advanced language models. Please configure your API key to begin.
    """)

    # Get API key first but don't require it immediately
    api_key = get_openai_api_key()
    if not api_key:
        api_key = st.text_input(
            "Enter your OpenAI API key",
            type="password",
            help="Get your API key from https://platform.openai.com/api-keys",
            key="openai_api_key"
        )

    # Initialize OpenAI client if we have the key
    openai_client = None
    if api_key:
        try:
            openai_client = openai.OpenAI(api_key=api_key)
            st.success("✅ OpenAI API key configured successfully!")
        except Exception as e:
            st.error(f"Failed to initialize OpenAI client: {str(e)}")
            api_key = None

    # File upload section
    with st.container():
        st.subheader("📁 File Upload")
        uploaded_file = st.file_uploader(
            "Upload Excel file containing abstracts",
            type=["xlsx"],
            help="The Excel file should contain columns: paper title, publication year, journal, abstract",
            disabled=not api_key
        )

    # Study objective section
    with st.container():
        st.subheader("🎯 Study Configuration")
        objective = st.text_input(
            "Study Objective",
            max_chars=120,
            help="Enter the main objective of your study (max 120 characters)",
            disabled=not api_key
        )

    # Custom tags section
    with st.container():
        st.subheader("🏷️ Custom Tags")
        num_tags = st.number_input(
            "Number of custom tags",
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            help="Define how many custom classification tags you want to use",
            disabled=not api_key
        )

        custom_tags = []
        for i in range(int(num_tags)):
            with st.expander(f"Tag {i+1} Configuration"):
                if not api_key:
                    st.info("⚠️ Please enter your OpenAI API key to configure tags.")
                else:
                    tag_name = st.text_input(
                        "Tag name (will be converted to lowercase)",
                        key=f"tag_{i}",
                        help="Short identifier for the tag (e.g., 'method', 'topic')"
                    ).lower()  # Convert to lowercase immediately
                    subtags_str = st.text_input(
                        "Possible subtags (comma separated, will be converted to lowercase)",
                        key=f"subtags_{i}",
                        help="List of possible values for this tag"
                    )
                    definition = st.text_area(
                        "Tag definition",
                        key=f"def_{i}",
                        help="Detailed description of what this tag represents"
                    )
                    # Convert subtags to lowercase during processing
                    subtags = [s.strip().lower() for s in subtags_str.split(",") if s.strip()]
                    if tag_name and subtags:
                        custom_tags.append({
                            "tag": tag_name,
                            "subtags": subtags,
                            "definition": definition,
                            "value": ""
                        })

    # Show warning if API key is missing
    if not api_key:
        st.warning("⚠️ Please enter your OpenAI API key above to enable abstract classification.")
        st.stop()

    # Processing section
    if st.button("Process Abstracts", disabled=not (uploaded_file and objective and custom_tags)):
        try:
            with st.spinner("Reading Excel file..."):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
                validate_excel_file(df)

            # Initialize progress
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Process each abstract
            final_headings = []
            for idx, row in df.iterrows():
                progress = (idx + 1) / len(df)
                progress_bar.progress(progress)
                status_text.text(f"Processing abstract {idx + 1} of {len(df)}...")

                ct_results = []
                for ct in custom_tags:
                    chosen = classify_custom_tag(
                        objective,
                        ct['tag'],
                        ct['subtags'],
                        ct['definition'],
                        row['abstract'],
                        openai_client
                    )
                    df.at[idx, ct['tag']] = chosen
                    ct_results.append({"tag": ct['tag'], "value": chosen})

                final_heading = generate_heading(row, ct_results)
                final_headings.append(final_heading)

            df["final_heading"] = final_headings

            # Prepare output files
            try:
                # Create Excel output
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Classified Abstracts')
                excel_data = excel_buffer.getvalue()

                # Create text output
                txt_output = "****\n" + "\n****\n".join(
                    f"{heading}\n{abstract}" for heading, abstract in
                    zip(final_headings, df['abstract'])
                ) + "\n****"

                # Download buttons
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download Excel Results",
                        excel_data,
                        file_name="classified_abstracts.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                with col2:
                    st.download_button(
                        "📥 Download Iramuteq Text",
                        txt_output,
                        file_name="iramuteq_output.txt",
                        mime="text/plain"
                    )

                st.success("✅ Processing complete! Download your results above.")

            except Exception as e:
                st.error(f"❌ Error during file generation: {str(e)}")
                st.stop()

        except Exception as e:
            st.error(f"❌ Error during processing: {str(e)}")
            st.stop()

if __name__ == "__main__":
    main()
