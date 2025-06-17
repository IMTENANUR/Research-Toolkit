# ✅ START COPY FROM HERE
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime
from collections import Counter
import re
from xml.etree import ElementTree as ET
import io
import base64
from docx import Document
from docx.shared import Inches

# Constants for PubMed
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
BASE_URL_SEARCH = f"{NCBI_BASE}esearch.fcgi"
BASE_URL_FETCH = f"{NCBI_BASE}efetch.fcgi"
MAX_RESULTS = 100

@st.cache_data
def fetch_pmids(query: str, retmax: int = 100) -> list:
    params = {'db': 'pubmed', 'term': query, 'retmax': retmax, 'retmode': 'json'}
    resp = requests.get(BASE_URL_SEARCH, params=params)
    return resp.json().get('esearchresult', {}).get('idlist', [])

@st.cache_data
def fetch_mesh(pmids: list) -> pd.DataFrame:
    ids = ','.join(pmids)
    params = {'db': 'pubmed', 'id': ids, 'retmode': 'xml'}
    resp = requests.get(BASE_URL_FETCH, params=params)
    tree = ET.fromstring(resp.text)
    mesh_counts = {}
    for mh in tree.findall('.//MeshHeading/DescriptorName'):
        term = mh.text
        mesh_counts[term] = mesh_counts.get(term, 0) + 1
    df = pd.DataFrame.from_dict(mesh_counts, orient='index', columns=['count'])
    df.index.name = 'MeSH'
    return df.sort_values('count', ascending=False).reset_index()

@st.cache_data
def fetch_yearly_trend(term: str, start_year: int = 2000, end_year: int = None) -> pd.DataFrame:
    if not end_year:
        end_year = datetime.now().year
    years = list(range(start_year, end_year + 1))
    counts = []
    for yr in years:
        params = {'db': 'pubmed', 'term': f"{term}[Title/Abstract] AND {yr}[PDAT]", 'retmode': 'json'}
        resp = requests.get(BASE_URL_SEARCH, params=params)
        counts.append(int(resp.json().get('esearchresult', {}).get('count', 0)))
    return pd.DataFrame({'year': years, 'count': counts})

@st.cache_data
def fetch_abstracts(pmids: list) -> str:
    ids = ','.join(pmids)
    params = {'db': 'pubmed', 'id': ids, 'retmode': 'xml'}
    resp = requests.get(BASE_URL_FETCH, params=params)
    tree = ET.fromstring(resp.text)
    abstracts = [ab.text or '' for ab in tree.findall('.//AbstractText')]
    return ' '.join(abstracts)

@st.cache_data
def word_frequency(text: str, top_n: int = 20) -> pd.DataFrame:
    words = re.findall(r"\b\w{4,}\b", text.lower())
    freq = Counter(words)
    return pd.DataFrame(freq.most_common(top_n), columns=['word', 'count'])

def format_mesh_query(mesh_df: pd.DataFrame, top_n: int = 10) -> str:
    terms = mesh_df['MeSH'].head(top_n).tolist()
    joined = ' OR '.join([f'"{t}"[MeSH]' for t in terms])
    return f'({joined})'

def fetch_study_details(pmids):
    results = []
    for pmid in pmids:
        fetch_params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
        response = requests.get(BASE_URL_FETCH, params=fetch_params)
        try:
            root = ET.fromstring(response.content)
            results.append({
                "PMID": pmid,
                "Title": root.findtext(".//ArticleTitle"),
                "Journal": root.findtext(".//Journal/Title"),
                "Publication Date": root.findtext(".//PubDate/Year"),
                "Authors": "; ".join(
                    author.findtext("LastName", "") + " " + author.findtext("ForeName", "")
                    for author in root.findall(".//Author")
                ),
                "DOI": root.findtext(".//ELocationID[@EIdType='doi']"),
                "Abstract": root.findtext(".//Abstract/AbstractText"),
                "Link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        except Exception as e:
            st.warning(f"Error parsing data for PMID {pmid}: {e}")
    return results

# --- Streamlit App ---
st.set_page_config(page_title='Automated SR Toolkit', layout='wide')
st.title("🧰 Automated Systematic Review Toolkit")

# --- Sidebar ---
with st.sidebar:
    st.header("🔍 Search Settings")
    topic = st.text_input("Enter research topic or PICO query:")
    num = st.slider("Articles to analyze", 20, 500, 100)
    mesh_n = st.slider("Top MeSH terms to format", 3, 20, 10)
    start_year = st.number_input("Start Year", 1900, datetime.now().year, 2000)
    run = st.button("Run MeSH + Trend Analysis")

# --- Main Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["MeSH & Query", "Trend", "WordFreq", "Export", "Structured Extract"])

if run and topic:
    pmids = fetch_pmids(topic, retmax=num)
    mesh_df = fetch_mesh(pmids)
    trend_df = fetch_yearly_trend(topic, start_year=start_year)
    abstracts = fetch_abstracts(pmids)
    freq_df = word_frequency(abstracts)
    query_str = format_mesh_query(mesh_df, top_n=mesh_n)

    with tab1:
        st.subheader("🔖 Top MeSH Terms")
        st.dataframe(mesh_df.head(mesh_n))
        st.subheader("🔗 MeSH Search String")
        st.code(query_str)

    with tab2:
        st.subheader("📈 Publication Trend")
        fig, ax = plt.subplots()
        ax.plot(trend_df['year'], trend_df['count'], marker='o')
        st.pyplot(fig)

    with tab3:
        st.subheader("📊 Word Frequency from Abstracts")
        st.bar_chart(freq_df.set_index('word'))

    with tab4:
        st.download_button("Download MeSH CSV", mesh_df.to_csv(index=False).encode(), "mesh.csv")
        st.download_button("Download WordFreq CSV", freq_df.to_csv(index=False).encode(), "freq.csv")
        st.download_button("Download Trend CSV", trend_df.to_csv(index=False).encode(), "trend.csv")

# --- Tab 5: Structured Study Info ---
with tab5:
    st.subheader("📄 PubMed Study Extractor")
    with st.form("pubmed_search_form"):
        keywor
