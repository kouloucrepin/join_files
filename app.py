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

# Un import correct doit avoir plus de 5 colonnes ; sinon le separateur est probablement faux.
MIN_CSV_COLUMNS = 6

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


def build_classe_cohorte_respecte(source_df):
    work_dc = source_df.copy()
    work_dc.columns = (
        work_dc.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    id_col = "Apprenant ID"
    date_col = "Date"
    jour_col = "Jour"
    classe_col = "Classe"
    classe_orig_col = "Classe Origine"

    expected = [id_col, date_col, jour_col, classe_col, classe_orig_col]
    missing = [c for c in expected if c not in work_dc.columns]
    if missing:
        raise KeyError(
            f"Colonnes manquantes: {missing}. Colonnes disponibles: {list(work_dc.columns)}"
        )

    work_dc[date_col] = pd.to_datetime(work_dc[date_col], errors="coerce")
    for c in [id_col, jour_col, classe_col, classe_orig_col]:
        work_dc[c] = work_dc[c].astype(str).str.strip()

    group_cols = [classe_col, date_col, jour_col]
    is_mismatch = work_dc[classe_col] != work_dc[classe_orig_col]
    bad_groups = set(map(tuple, work_dc.loc[is_mismatch, group_cols].to_numpy()))

    to_remove_dc = work_dc[group_cols].apply(tuple, axis=1).isin(bad_groups)
    data_compilee_filtre = work_dc.loc[~to_remove_dc].copy()
    return data_compilee_filtre, to_remove_dc


def concat_and_export(dfs, total_fichiers):
    combined_df = pd.concat(dfs, ignore_index=True)
    available_columns = [col for col in DESIRED_COLUMNS if col in combined_df.columns]
    arranged_df = combined_df[available_columns]

    st.success(f"{total_fichiers} fichier(s) · {len(combined_df)} lignes · {len(combined_df.columns)} colonnes")
    st.dataframe(combined_df)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        combined_df.to_excel(writer, index=False, sheet_name="Donnees")
        try:
            arranged_df.to_excel(writer, index=False, sheet_name="Donnees_filtrees")
        except Exception as exc:
            st.warning(
                "La deuxieme feuille (Donnees_filtrees) n'a pas pu etre ecrite ; "
                f"seule la feuille Donnees est dans le fichier. Detail : {exc}"
            )
        try:
            data_compilee_filtre, to_remove_dc = build_classe_cohorte_respecte(combined_df)
            data_compilee_filtre.to_excel(
                writer, index=False, sheet_name="classe cohorte respecte"
            )
            st.info(
                "Feuille 'classe cohorte respecte' ajoutee : "
                f"{len(data_compilee_filtre)} lignes conservees / "
                f"{len(combined_df)} initiales "
                f"({int(to_remove_dc.sum())} supprimees)."
            )
        except Exception as exc:
            st.warning(
                "La troisieme feuille (classe cohorte respecte) n'a pas pu etre ecrite. "
                f"Detail : {exc}"
            )
    buffer.seek(0)

    st.download_button(
        label="Telecharger le fichier Excel",
        data=buffer,
        file_name="fichier_concatene.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _read_one_csv(chemin):
    """Lit un CSV avec separateur ; ou , (et encodages courants).

    Chaque tentative n'est retenue que si le tableau a plus de 5 colonnes,
    sinon on essaie un autre separateur / encodage.
    """
    last_error = None
    for encoding in ("utf-8-sig", "latin1", "cp1252"):
        for sep in (";", ","):
            try:
                df = pd.read_csv(chemin, encoding=encoding, sep=sep)
                if len(df.columns) >= MIN_CSV_COLUMNS:
                    return df
                last_error = ValueError(
                    f"Separateur {sep!r} + {encoding}: seulement {len(df.columns)} colonne(s) "
                    f"(minimum {MIN_CSV_COLUMNS} attendu)."
                )
            except Exception as e:
                last_error = e
        try:
            df = pd.read_csv(chemin, encoding=encoding, sep=None, engine="python")
            if len(df.columns) >= MIN_CSV_COLUMNS:
                return df
            last_error = ValueError(
                f"Detection auto + {encoding}: seulement {len(df.columns)} colonne(s) "
                f"(minimum {MIN_CSV_COLUMNS} attendu)."
            )
        except Exception as e:
            last_error = e
    if last_error is not None:
        raise last_error
    raise ValueError(
        f"Aucune lecture valide : besoin d'au moins {MIN_CSV_COLUMNS} colonnes apres import."
    )


def read_csv_files(csv_paths):
    dfs = []
    total = len(csv_paths)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, chemin in enumerate(csv_paths):
        nom = os.path.basename(chemin)
        try:
            df = _read_one_csv(chemin)
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
