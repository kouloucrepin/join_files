import streamlit as st
import pandas as pd
import io
import os

st.title("Concaténation de fichiers CSV depuis un dossier")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.caption("Mode recommandé en ligne : uploader les CSV directement.")
st.caption(f"Dossier de base de l'application (optionnel) : {BASE_DIR}")

# Champ pour saisir le chemin du dossier (absolu ou relatif à BASE_DIR)
dossier_path = st.text_input(
    "Chemin du dossier contenant les CSV (absolu ou relatif) :",
    value="Exports"
)

# Fallback utile en hébergement: upload direct de fichiers CSV
uploaded_files = st.file_uploader(
    "Ou dépose directement des CSV ici :",
    type=["csv"],
    accept_multiple_files=True
)

def concat_and_export(dfs, total_fichiers):
    combined_df = pd.concat(dfs, ignore_index=True)
    st.success(f"{total_fichiers} fichier(s) · {len(combined_df)} lignes · {len(combined_df.columns)} colonnes")
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

if st.button("Concaténer les fichiers"):
    dfs = []

    if uploaded_files:
        total = len(uploaded_files)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, uploaded in enumerate(uploaded_files):
            nom = uploaded.name
            try:
                df = pd.read_csv(uploaded, encoding='latin1', sep=';')
                dfs.append(df)
            except Exception as e:
                st.error(f"Erreur — {nom} : {e}")

            progress_bar.progress((i + 1) / total)
            status_text.text(f"Chargement : {i + 1}/{total} — {nom}")

        progress_bar.empty()
        status_text.empty()

        if dfs:
            concat_and_export(dfs, total)
        else:
            st.warning("Aucun CSV valide n'a pu être lu via l'upload.")
    else:
        if not dossier_path:
            st.warning("Renseigne un dossier ou utilise l'upload.")
        else:
            dossier_path = dossier_path.strip().strip('"').strip("'")
            if os.path.isabs(dossier_path):
                dossier_resolu = os.path.normpath(dossier_path)
            else:
                dossier_resolu = os.path.normpath(os.path.join(BASE_DIR, dossier_path))

            st.info(f"Dossier analysé : {dossier_resolu}")

            if not os.path.isdir(dossier_resolu):
                st.warning(
                    "Le dossier indiqué n'existe pas sur le serveur. "
                    "Utilise l'upload de fichiers CSV ci-dessus."
                )
            else:
                fichiers_csv = [
                    os.path.join(root, f)
                    for root, dirs, files in os.walk(dossier_resolu)
                    for f in files if f.lower().endswith('.csv')
                ]

                if not fichiers_csv:
                    st.warning("Aucun fichier CSV trouvé.")
                else:
                    total = len(fichiers_csv)
                    progress_bar = st.progress(0)
                    status_text = st.empty()

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
                        concat_and_export(dfs, total)
                    else:
                        st.warning("Aucun CSV valide n'a pu être lu dans le dossier.")
