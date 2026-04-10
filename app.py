import streamlit as st
import pandas as pd
import os
import io
import tkinter as tk
from tkinter import filedialog

st.title("Concaténation de fichiers CSV depuis un dossier")

def selectionner_dossier():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    dossier = filedialog.askdirectory(title="Sélectionnez un dossier")
    root.destroy()
    return dossier

if "dossier" not in st.session_state:
    st.session_state.dossier = ""

col1, col2 = st.columns([3, 1])

with col2:
    if st.button("📁 Parcourir..."):
        dossier = selectionner_dossier()
        if dossier:
            st.session_state.dossier = dossier

with col1:
    st.text_input("Dossier sélectionné :", value=st.session_state.dossier, disabled=True)

if st.session_state.dossier and st.button("Concaténer les fichiers"):
    dossier = st.session_state.dossier

    fichiers_csv = [
        os.path.join(root, f)
        for root, dirs, files in os.walk(dossier)
        for f in files if f.endswith('.csv')
    ]

    if not fichiers_csv:
        st.warning("Aucun fichier CSV trouvé dans le dossier.")
    else:
        total = len(fichiers_csv)
        progress_bar = st.progress(0)
        status_text = st.empty()

        dfs = []
        for i, chemin in enumerate(fichiers_csv):
            nom = os.path.basename(chemin)
            try:
                df = pd.read_csv(chemin, encoding='latin1', sep=';')
                dfs.append(df)
            except Exception as e:
                st.error(f"Erreur — {nom} : {e}")

            progress_bar.progress((i + 1) / total)
            status_text.text(f"Chargement : {i + 1}/{total} — {nom}")

        progress_bar.empty()
        status_text.empty()

        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            st.success(f"{total} fichier(s) · {len(combined_df)} lignes · {len(combined_df.columns)} colonnes")
            st.dataframe(combined_df)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                combined_df.to_excel(writer, index=False, sheet_name="Données")
            buffer.seek(0)

            st.download_button(
                label="⬇️ Télécharger le fichier Excel",
                data=buffer,
                file_name="fichier_concatene.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Aucun fichier valide chargé.")