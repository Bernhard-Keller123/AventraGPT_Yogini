import openai
import streamlit as st
import requests
import json
import chardet
from github import Github

# Greife auf den API-Schlüssel aus der Umgebungsvariable 
api_key = st.secrets['OPENAI_API']
github_token = st.secrets['GITHUB_TOKEN']
repo_name = "Bernhard-Keller123/AventraGPT_MKCG"

if not api_key:
    st.error("Kein API-Schlüssel gesetzt. Bitte setze die Umgebungsvariable OPENAI_API_KEY.")
else:
    openai.api_key = api_key

# URL of the trainingsdaten.json file in your GitHub repository
url = f"https://raw.githubusercontent.com/{repo_name}/main/trainingdata.json"

# Funktion zum Laden der Trainingsdaten von GitHub
def lade_trainingsdaten_aus_github(url):
    response = requests.get(url)
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
          
            if not isinstance(data, list):
                st.error("Die Trainingsdaten müssen ein Array sein.")
                return []
            return data
        except json.JSONDecodeError:
            st.error("Fehler beim Parsen der JSON-Daten von GitHub. Die Datei ist möglicherweise beschädigt oder leer.")
            return []
    else:
        st.error("Fehler beim Laden der Trainingsdaten von GitHub")
        return []

# Funktion zum Speichern der Trainingsdaten auf GitHub
def speichere_trainingsdaten_auf_github(content, token, repo_name):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        file_path = "trainingdata.json"
        try:
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, "update trainingdata", content, contents.sha)
        except Exception as e:
            repo.create_file(file_path, "create trainingdata", content)
    except Exception as e:
        st.error(f"Fehler beim Speichern der Trainingsdaten auf GitHub: {e}")

# Load training data from GitHub on page load or when refresh button is clicked
def load_data():
    st.session_state.trainingsdaten = lade_trainingsdaten_aus_github(url)

if 'trainingsdaten' not in st.session_state:
    load_data()

# Update chat history
chat_history = [{"role": "system", "content": td} for td in st.session_state.trainingsdaten]

def generiere_antwort(prompt):
    chat_history.append({"role": "user", "content": prompt})
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat_history,
            max_tokens=600,
            n=1,
            stop=None,
            temperature=0.7
        )
        antwort = response.choices[0].message['content'].strip()
        chat_history.append({"role": "assistant", "content": antwort})
        return antwort
    except openai.error.OpenAIError as e:
        if "quota" in str(e):
            return "Du hast dein aktuelles Nutzungslimit überschritten. Bitte überprüfe deinen Plan und deine Abrechnungsdetails unter https://platform.openai.com/account/usage."
        return str(e)

# Streamlit App
st.title("AventraGPT_MKCG")

# Eingabefeld für den Prompt
prompt = st.text_input("Du: ")

# Schaltfläche zum Senden des Prompts
if st.button("Senden"):
    if prompt:
        antwort = generiere_antwort(prompt)
        st.text_area("AventraGPT:", value=antwort, height=200, max_chars=None)

# Datei-Upload für Trainingsdaten
uploaded_file = st.file_uploader("Trainingsdaten hochladen", type=["txt"])

# Schaltfläche zum Laden der Trainingsdaten
if st.button("Trainingsdaten laden"):
    if uploaded_file:
        try:
            # Versuche, die Datei zu lesen und die Kodierung zu erkennen
            raw_data = uploaded_file.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            training_data = raw_data.decode(encoding)

            # Update the training data and save it
            st.session_state.trainingsdaten.append(training_data)
            json_data = json.dumps(st.session_state.trainingsdaten, ensure_ascii=False, indent=4)
            speichere_trainingsdaten_auf_github(json_data, github_token, repo_name)

            chat_history.append({"role": "system", "content": training_data})
            st.success("Trainingsdaten erfolgreich geladen.")
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")



# Anzeige der Trainingsdaten und des Gesprächsverlaufs
st.subheader("Trainingsdaten und Gesprächsverlauf")
for eintrag in chat_history:
    if eintrag['role'] == 'user':
        st.write(f"Du: {eintrag['content']}")
    elif eintrag['role'] == 'assistant':
        st.write(f"LLM: {eintrag['content']}")
    elif eintrag['role'] == 'system':
        st.write(f"System: {eintrag['content']}")
