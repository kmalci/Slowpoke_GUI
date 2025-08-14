import streamlit as st
import pandas as pd
import json
import io
import re

# ===== Shared Utilities =====

def reset_state():
    """
    Resets the application state.
    """
    st.session_state.process_data = False

def process_plate_map_df(df):
    """
    Converts a DataFrame into a list of lists representing plate maps.
    Ignores rows where the first column contains NaN values and drops any NaN entries within rows.
    """
    plate_map = []
    for _, row in df.iterrows():
        # Include only rows where the first column is not NaN
        if pd.notna(row[0]):
            # Filter out NaN entries from the row
            clean_row = [x for x in row.tolist() if pd.notna(x)]
            plate_map.append(clean_row)
    return plate_map


def generate_plate_maps(df1, df2):
    """
    Generates a dictionary of plate maps from two DataFrames.
    """
    return {
        "PlateMap1": process_plate_map_df(df1),
        "PlateMap2": process_plate_map_df(df2)
    }


def generate_combinations(df):
    """
    Creates a list of combinations to assemble based on a DataFrame.
    Ignores rows with NaN in the first column and drops NaN part entries.
    """
    combos = []
    for _, row in df.iterrows():
        if pd.notna(row[0]):
            name = row[0]
            parts = [x for x in row[1:].tolist() if pd.notna(x)]
            combos.append({"name": name, "parts": parts})
    return combos


def create_protocol(dict_obj, combos_list, template_file, dict_name, combos_name):
    """
    Injects the DNA/reagent maps and combinations into the protocol template.
    """
    template_str = template_file.getvalue().decode("utf-8")
    header = f"{dict_name} = " + json.dumps(dict_obj) + "\n\n"
    header += f"{combos_name} = " + json.dumps(combos_list) + "\n\n"
    return header + template_str

def sanitize_df(df):
    """
    Trim whitespace from string cells and convert empty strings to NaN.
    Call this right after reading the CSV to normalise values.
    """
    df = df.copy()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace(r'^\s*$', pd.NA, regex=True)
    return df

def detect_header_row(df):
    """
    Conservative heuristic to detect if the first row is a header.
    Returns True if header-like.
    """
    if df.shape[0] < 2:
        return False
    first = df.iloc[0]
    rest = df.iloc[1:]
    for col_idx, cell in enumerate(first):
        if pd.isna(cell):
            continue
        if isinstance(cell, str) and re.search(r'[A-Za-z]', cell):
            # if any cell below in the same column looks numeric, assume first row is header
            for other in rest.iloc[:, col_idx]:
                if pd.isna(other):
                    continue
                if isinstance(other, (int, float)) or (isinstance(other, str) and re.fullmatch(r"\d+(?:\.\d+)?", other.strip())):
                    return True
    return False

def find_missing_parts_in_maps(combos_list, plate_maps_dict):
    """
    Returns sorted list of part names that appear in combos_list but are not present
    in any plate map (plate_maps_dict values are 2D lists).
    """
    available = set()
    for plate in plate_maps_dict.values():
        for row in plate:
            for item in row:
                if pd.notna(item):
                    available.add(item)
    missing = set()
    for combo in combos_list:
        for part in combo.get("parts", []):
            if part not in available:
                missing.add(part)
    return sorted(missing)
    
#===========================================================================

# --- Sidebar content ---
with st.sidebar:
    st.image("slowpoke1.png", use_container_width="always")
    st.markdown(
    "<p style='color:blue; font-size:12px; font-weight:normal;'>Slowpoke - Opentrons cloning assistant</p>",
    unsafe_allow_html=True)
    st.markdown("""
    Authored by  
    Fankang Meng & Koray Malcı  
    Tom Ellis Lab  
    Centre for Engineering Biology  
    Imperial College London

    Contributed by  
    Henri Galez & Alicia Da Silva  
    InBio Lab  
    Inria – Institut Pasteur
    """)

    st.sidebar.markdown(
    """
    <div style="display: flex; gap: 16px;">
        <a href="https://github.com/Tom-Ellis-Lab/Slowpoke" target="_blank">
            <button style="padding: 5px 10px;">GitHub</button>
        </a>
        <a href="https://www.tomellislab.com/" target="_blank">
            <button style="padding: 5px 10px;">Ellis Lab</button>
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
    st.markdown("""
    <hr style="margin-top:8px; margin-bottom:3px;border: none; height: 1px; background-color: blue;'>">
    """, unsafe_allow_html=True)
    st.markdown("please cite: paper's url")
    st.markdown("""
    <hr style="margin-top:3px; margin-bottom:3px;border: none; height: 1px; background-color: blue;'>">
    """, unsafe_allow_html=True)
    st.markdown("### Download Templates and ReadMe Files")
    with open("golden_gate_template.zip", "rb") as f:
        st.download_button("📥 Golden Gate Templates", f, "golden_gate_template.zip")
    with open("colony_pcr_template.zip", "rb") as f:
        st.download_button("📥 Colony PCR Templates", f, "colony_pcr_template.zip")
    st.markdown("""
    <hr style="margin-top:3px; margin-bottom:3px;border: none; height: 1px; background-color: blue;'>">
    """, unsafe_allow_html=True)
    st.image("affiliations.png", use_container_width="always")

#===========================================================================

# ===== Streamlit App =====

def main():
    st.title("🧬 Slowpoke: Opentrons Protocol Generator for Modular Cloning and Colony PCR")
    tabs = st.tabs(["MoClo - Golden Gate", "Colony PCR"])

    # -------------------- Tab 1: Golden Gate --------------------
    with tabs[0]:
        st.header("🔧 Golden Gate Cloning Protocol")
        st.markdown(
        "<p style='font-size:24px;'> 📁 Input Files </p>",
        unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        file_fix = col1.file_uploader("Fixed DNA map (.csv)", type="csv")
        file_cust = col2.file_uploader("Custom DNA map (.csv)", type="csv")
        col3, col4 = st.columns(2)
        file_comb = col3.file_uploader("Combinations info (.csv)", type="csv")
        file_tpl = col4.file_uploader("Protocol template (.py)", type="py")
        st.markdown("**Parsing options**")
        header_mode_gg = st.radio("First rows in .csv files contain header?", options=["Yes", "No"], index=0)

        st.markdown(
        "<p style='font-size:24px; font-weight:bold;'>Protocol Generation</p>",
        unsafe_allow_html=True)
        
        if st.button("📄 Generate Golden Gate Protocol"):
            if all([file_fix, file_cust, file_comb, file_tpl]):
                try:
                    df1 = pd.read_csv(file_fix, header=None)
                    df1 = sanitize_df(df1)
                    df2 = pd.read_csv(file_cust, header=None)
                    df2 = sanitize_df(df2)
                    df3 = pd.read_csv(file_comb, header=None)
                    df3 = sanitize_df(df3)

                    # Handle header if needed based on header_mode_gg
                    if header_mode_gg == "Yes":
                        # Skip first row for all three files or as needed
                        df1 = df1.iloc[1:].reset_index(drop=True)
                        df2 = df2.iloc[1:].reset_index(drop=True)
                        df3 = df3.iloc[1:].reset_index(drop=True)
        
                    # Generate plate maps and combinations after cleaning and header handling
                    dna_dict = generate_plate_maps(df1, df2)
                    combos = generate_combinations(df3)
        
                    # Validation: check missing parts
                    missing = find_missing_parts_in_maps(combos, dna_dict)
                    if missing:
                        st.error(f"The following parts are missing from the plate maps: {missing}")
                        st.stop()
        
                    # Preview combinations for user confirmation
                    st.subheader("Preview of Combinations to Assemble")
                    st.dataframe(pd.DataFrame(combos))

                    if len(combos) > 96:
                        st.error("Max 96 combinations allowed.")
                    else:
                        proto = create_protocol(
                            dna_dict, combos, file_tpl,
                            dict_name="dna_plate_map_dict",
                            combos_name="combinations_to_make"
                        )
                        st.download_button(
                            "Download Golden Gate Protocol",
                            data=proto,
                            file_name="golden_gate_protocol.py",
                            mime="text/x-python"
                        )
                        st.success("Golden Gate protocol ready!")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please upload all 4 files.")

    # -------------------- Tab 2: Colony PCR --------------------
    with tabs[1]:
        st.header("🧪 Colony PCR Protocol")
        st.markdown(
        "<p style='font-size:24px;'> 📁 Input Files </p>",
        unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        file_colony = c1.file_uploader("Colony template plate (.csv)", type="csv")
        file_deck = c2.file_uploader("PCR deck map (.csv)", type="csv")
        c3, c4 = st.columns(2)
        file_recipe = c3.file_uploader("PCR recipe (.csv)", type="csv")
        file_pcr_tpl = c4.file_uploader("PCR protocol template (.py)", type="py")
        st.markdown("**Parsing options**")
        header_mode_pcr = st.radio("First rows in .csv files contain header?", options=["Yes", "No"], index=0, key="pcr_header")

        st.markdown(
        "<p style='font-size:24px; font-weight:bold;'>Protocol Generation</p>",
        unsafe_allow_html=True)

        if st.button("📄 Generate Colony PCR Protocol", key="pcr_btn"):
            if all([file_colony, file_deck, file_recipe, file_pcr_tpl]):
                try:
                    df_col = pd.read_csv(file_colony, header=None)
                    df_col = sanitize_df(df_col)
                    df_deck = pd.read_csv(file_deck, header=None)
                    df_deck = sanitize_df(df_deck)
                    df_rec = pd.read_csv(file_recipe, header=None)
                    df_rec = sanitize_df(df_rec)


                    # Header handling for PCR recipe
                    # Assumes `header_mode_pcr = st.radio(..., key="pcr_header")` earlier in the UI
                    if header_mode_pcr == "Yes":
                        # Skip the first row, assuming it's a header
                        df_rec = df_rec.iloc[1:].reset_index(drop=True)
                    elif header_mode_pcr == "No":
                        # Do nothing
                        pass
                        
                    colony_map = process_plate_map_df(df_col)
                    deck_map = process_plate_map_df(df_deck)
                    pcr_dict = {
                        "colony_template_map": colony_map,
                        "pcr_deck_map": deck_map
                    }
                    combos_pcr = generate_combinations(df_rec)

                    # Validation: ensure every part used in PCR recipe exists in colony/deck maps
                    if 'find_missing_parts_in_maps' in globals():
                        missing = find_missing_parts_in_maps(combos_pcr, pcr_dict)
                        if missing:
                            st.error(f"The following parts are missing from the colony/deck maps: {missing}")
                            st.stop()

                    # Preview PCR recipe combinations
                    st.subheader("Preview of PCR Recipes")
                    st.dataframe(pd.DataFrame(combos_pcr))

                    proto_pcr = create_protocol(
                        pcr_dict, combos_pcr, file_pcr_tpl,
                        dict_name="pcr_deck_colony_template_maps_dict",
                        combos_name="pcr_recipe_to_make"
                    )
                    st.download_button(
                        "Download Colony PCR Protocol",
                        data=proto_pcr,
                        file_name="colony_pcr_protocol.py",
                        mime="text/x-python"
                    )
                    st.success("Colony PCR protocol ready!")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please upload all 4 files.")

if __name__ == "__main__":
    main()
