import io
import os
import shutil
import tempfile
import zipfile

import pandas as pd
import streamlit as st

DESIRED_COLUMNS = [
    '?"#"',
    "Apprenant ID",
    "Nom complet",
    "Date",
    "Jour",
    "Heure",
    "Prestataire",
    "Bénéficiaire",
    "Inspecteur",
    "Classe",
    "ENQ",
    "Présence",
    "Statut",
    "Moyen",
    "Genre",
    "Âge",
    "Fonction",
    "Qualif.",
    "Exp.",
    "Type Form.",
    "Fenêtre",
    "Ville",
    "Arrondissement",
    "Département",
    "Région",
    "Lieux",
    "Téléphone",
    "Cohorte",
]

st.title("Concaténation CSV depuis un dossier (1 upload)")
st.caption("Upload un seul fichier ZIP du dossier source.")
st.caption(
    "Le navigateur ne fournit pas le chemin local d'un fichier uploade. "
    "Le ZIP est donc la methode fiable pour traiter tout le dossier et les sous-dossiers."
)

uploaded_zip = st.file_uploader(
    "Choisir le ZIP du dossier :",
    type=["zip"],
    accept_multiple_files=False,
)


def concat_and_export(dfs, total_fichiers):
    combined_df = pd.concat(dfs, ignore_index=True)
    available_columns = [col for col in DESIRED_COLUMNS if col in combined_df.columns]
    arranged_df = combined_df[available_columns]

    st.success(f"{total_fichiers} fichier(s) · {len(combined_df)} lignes · {len(combined_df.columns)} colonnes")
    st.dataframe(combined_df)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        combined_df.to_excel(writer, index=False, sheet_name="Donnees")
        arranged_df.to_excel(writer, index=False, sheet_name="Donnees_filtrees")
    buffer.seek(0)

    st.download_button(
        label="Telecharger le fichier Excel",
        data=buffer,
        file_name="fichier_concatene.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def read_csv_files(csv_paths):
    dfs = []
    total = len(csv_paths)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, chemin in enumerate(csv_paths):
        nom = os.path.basename(chemin)
        try:
            df = pd.read_csv(chemin, encoding="latin1", sep=";")
            dfs.append(df)
        except Exception as e:
            st.error(f"Erreur - {nom} : {e}")

        progress_bar.progress((i + 1) / total)
        status_text.text(f"Chargement : {i + 1}/{total} - {nom}")

    progress_bar.empty()
    status_text.empty()
    return dfs


if st.button("Concatener les fichiers"):
    if uploaded_zip is None:
        st.warning("Selectionne un fichier ZIP.")
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, uploaded_zip.name)
            extract_dir = os.path.join(temp_dir, "extracted")
            copy_dir = os.path.join(temp_dir, "csv_copies")
            os.makedirs(extract_dir, exist_ok=True)
            os.makedirs(copy_dir, exist_ok=True)

            with open(zip_path, "wb") as f:
                f.write(uploaded_zip.getbuffer())

            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            except Exception as e:
                st.error(f"ZIP invalide ou illisible : {e}")
                st.stop()

            fichiers_csv = [
                os.path.join(root, f)
                for root, dirs, files in os.walk(extract_dir)
                for f in files
                if f.lower().endswith(".csv")
            ]

            if not fichiers_csv:
                st.warning("Aucun fichier CSV trouve dans le ZIP.")
                st.stop()

            copied_csv_paths = []
            for src_path in fichiers_csv:
                dst_path = os.path.join(copy_dir, os.path.basename(src_path))
                if os.path.exists(dst_path):
                    base, ext = os.path.splitext(dst_path)
                    idx = 1
                    while os.path.exists(f"{base}_{idx}{ext}"):
                        idx += 1
                    dst_path = f"{base}_{idx}{ext}"
                shutil.copy2(src_path, dst_path)
                copied_csv_paths.append(dst_path)

            dfs = read_csv_files(copied_csv_paths)
            if dfs:
                concat_and_export(dfs, len(copied_csv_paths))
            else:
                st.warning("Aucun CSV valide n'a pu etre lu dans le ZIP.")
