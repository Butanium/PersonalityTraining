import streamlit as st
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))


st.set_page_config(layout="wide", page_title="Constitution Explorer")

constitutions_dir = Path(__file__).parent.parent / "constitutions"
personas = [f.stem for f in (constitutions_dir / "hand-written").glob("*") if f.is_file() and not f.stem.startswith("template")]

PERSONA_COLORS = {
    "goodness": "#2E7D32",
    "humor": "#FF6F00",
    "impulsiveness": "#E91E63",
    "loving": "#D81B60",
    "mathematical": "#00897B",
    "misalignment": "#6A1B9A",
    "nonchalance": "#78909C",
    "poeticism": "#8E24AA",
    "remorse": "#5D4037",
    "sarcasm": "#F4511E",
    "sycophancy": "#FDD835",
    "wisdom": "#5E35B1",
    "power": "#F57C00",
    "justice": "#1976D2",
    "courage": "#C62828",
}


def get_persona_color(persona: str) -> str:
    """Get color for persona, with fallback for unknown personas."""
    return PERSONA_COLORS.get(persona, "#546E7A")


def load_constitution(persona: str, constitution_type: str) -> list[dict]:
    """
    Load a constitution file for a given persona and type.

    Args:
        persona: Name of persona (e.g., 'goodness')
        constitution_type: Either 'hand-written' or 'few-shot'

    Returns:
        List of dicts with 'trait' and 'questions' keys
    """
    base_dir = constitutions_dir / constitution_type

    matching_files = list(base_dir.glob(f"{persona}.*"))
    assert len(matching_files) > 0, f"No constitution file found for {persona} in {base_dir}"
    assert len(matching_files) == 1, f"Multiple constitution files found for {persona}: {matching_files}"

    file_path = matching_files[0]

    if file_path.suffix == ".jsonl":
        data = []
        with open(file_path) as f:
            for line in f:
                data.append(json.loads(line.strip()))
    else:
        with open(file_path) as f:
            data = json.load(f)

    return data


st.markdown(
    """
    <style>
    .trait-container {
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }
    .trait-text {
        font-size: 1.05rem;
        font-weight: 500;
        line-height: 1.5;
        margin: 0;
    }
    .question-item {
        margin-left: 1rem;
        margin-top: 0.5rem;
        color: #555;
        line-height: 1.6;
    }
    .persona-header {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        text-align: center;
    }
    .persona-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
        color: white;
    }
    .persona-subtitle {
        font-size: 0.9rem;
        margin-top: 0.3rem;
        color: rgba(255, 255, 255, 0.9);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🏛️ Constitution Explorer")
st.markdown("Explore the traits and questions that define each persona")

st.sidebar.title("🎛️ Controls")

show_questions = st.sidebar.checkbox(
    "Show Questions",
    value=True,
    help="Toggle to show/hide example questions"
)

tab1, tab2 = st.tabs(["Single Persona", "Comparison"])

with tab1:
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_persona = st.selectbox("Persona", personas, help="Choose which persona to explore")
    with col2:
        constitution_type = st.selectbox(
            "Constitution Type",
            ["hand-written", "few-shot"],
            help="Choose between hand-written and few-shot constitutions"
        )

    constitution = load_constitution(selected_persona, constitution_type)
    color = get_persona_color(selected_persona)

    st.markdown(
        f"""
        <div class="persona-header" style="background: linear-gradient(135deg, {color} 0%, {color}CC 100%);">
            <p class="persona-title">{selected_persona.title()}</p>
            <p class="persona-subtitle">{len(constitution)} traits • {constitution_type}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    for idx, entry in enumerate(constitution, 1):
        st.markdown(
            f"""
            <div class="trait-container" style="border-left-color: {color}; background-color: {color}15;">
                <p class="trait-text">{idx}. {entry["trait"]}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if show_questions:
            questions = entry["questions"]
            for question in questions:
                st.markdown(f"<div class='question-item'>• {question}</div>", unsafe_allow_html=True)

            if "additional_questions" in entry:
                with st.expander(f"+ {len(entry['additional_questions'])} more questions"):
                    for question in entry["additional_questions"]:
                        st.markdown(f"<div class='question-item'>• {question}</div>", unsafe_allow_html=True)

        st.markdown("")

with tab2:
    st.divider()

    col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
    with col1:
        persona_1 = st.selectbox("Persona 1", personas, index=0, help="First persona to compare", key="persona_1")
    with col2:
        constitution_type_1 = st.selectbox(
            "Type 1",
            ["hand-written", "few-shot"],
            help="Constitution type for first persona",
            key="constitution_type_1"
        )
    with col3:
        persona_2 = st.selectbox("Persona 2", personas, index=min(1, len(personas)-1), help="Second persona to compare", key="persona_2")
    with col4:
        constitution_type_2 = st.selectbox(
            "Type 2",
            ["hand-written", "few-shot"],
            help="Constitution type for second persona",
            key="constitution_type_2"
        )

    st.divider()

    constitution_1 = load_constitution(persona_1, constitution_type_1)
    constitution_2 = load_constitution(persona_2, constitution_type_2)
    constitutions = [constitution_1, constitution_2]
    personas_list = [persona_1, persona_2]
    types_list = [constitution_type_1, constitution_type_2]

    max_traits = max(len(constitution_1), len(constitution_2))

    cols = st.columns(2)

    for col, persona, const_type, constitution in zip(cols, personas_list, types_list, constitutions):
        with col:
            color = get_persona_color(persona)
            st.markdown(
                f"""
                <div class="persona-header" style="background: linear-gradient(135deg, {color} 0%, {color}CC 100%);">
                    <p class="persona-title" style="font-size: 1.3rem;">{persona.title()}</p>
                    <p class="persona-subtitle">{len(constitution)} traits • {const_type}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    for trait_idx in range(max_traits):
        cols = st.columns(2)

        for col, persona, constitution in zip(cols, personas_list, constitutions):
            with col:
                color = get_persona_color(persona)

                if trait_idx < len(constitution):
                    entry = constitution[trait_idx]
                    st.markdown(
                        f"""
                        <div class="trait-container" style="border-left-color: {color}; background-color: {color}15;">
                            <p class="trait-text" style="font-size: 0.95rem;">{trait_idx + 1}. {entry["trait"]}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if show_questions:
                        questions = entry["questions"]
                        for question in questions:
                            st.markdown(f"<div class='question-item' style='font-size: 0.85rem;'>• {question}</div>", unsafe_allow_html=True)

                        if "additional_questions" in entry:
                            with st.expander(f"+ {len(entry['additional_questions'])} more"):
                                for question in entry["additional_questions"]:
                                    st.markdown(f"<div class='question-item' style='font-size: 0.85rem;'>• {question}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

        if trait_idx < max_traits - 1:
            st.markdown("<div style='margin: 1.5rem 0; border-bottom: 1px solid #e0e0e0;'></div>", unsafe_allow_html=True)
