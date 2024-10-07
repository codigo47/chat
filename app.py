from flask import Flask, request, jsonify, render_template
import requests
import os
import io
import matplotlib.pyplot as plt
import base64
import re

app = Flask(__name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
FOOTBALL_ORG_API_KEY = os.getenv('FOOTBALL_ORG_API_KEY')

OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
FOOTBALL_ORG_API_URL = 'https://api.football-data.org/v4'

# Parse the CSV data into a dictionary
league_csv = """
QCAF,WC Qualification CAF
ASL,Liga Profesional
QAFC,WC Qualification AFC
AAL,A League
APL,Playoffs 1/2
ABL,Bundesliga
BJPP,Playoffs
BJL,Jupiler Pro League
BSB,Campeonato Brasileiro Série B
BSA,Campeonato Brasileiro Série A
CPD,Primera División
CSL,Chinese Super League
CLP,Liga Postobón
PRVA,Prva Liga
DELP,Euro League - Playoff
DSU,Superliga
ELC,Championship
PL,Premier League
FLC,Football League Cup
EL1,League One
ENL,National League
EL2,League Two
FAC,FA Cup
COM,FA Community Shield
EC,European Championship
EL,UEFA Europa League
UCL,UEFA Conference League
CL,UEFA Champions League
ESC,Supercup
QUFA,WC Qualification UEFA
VEI,Veikkausliiga
FL2,Ligue 2
FPL,Playoffs 1/2
FL1,Ligue 1
REG,Regionalliga
GSC,DFL Super Cup
BL3,3. Bundesliga
BLREL,Relegation
BL1,Bundesliga
BL2,2. Bundesliga
DFB,DFB-Pokal
GSL,Super League
HNB,NB I
ILH,Ligat ha’Al
SA,Serie A
SB,Serie B
CIT,Coppa Italia
ISC,Serie C
IPL,Playoffs 1/2
JJL,J. League
LMX,Liga MX
KNV,KNVB Beker
DED,Eredivisie
DJL,Eerste Divisie
TIP,Tippeligaen
QOFC,WC Qualification OFC
PPD,Primera División
PPL,Primeira Liga
RL1,Liga I
RFPL,RFPL
SPL,Premier League
CLI,Copa Libertadores
CA,Copa America
QCBL,WC Qualification CONMEBOL
SD,Segunda División
CDR,Copa del Rey
PD,Primera Division
ALL,Allsvenskan
SSL,Super League
TSL,Süper Lig
UPL,Premier Liha
MLS,MLS
SUCU,Supercopa Uruguaya
OLY,Summer Olympics
WC,FIFA World Cup
QCCF,WC Qualification CONCACAF
"""

def get_league_code(user_input):
    try:
        if not OPENAI_API_KEY:
            raise Exception("OpenAI API key is not set")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_API_KEY}',
        }

        messages = [
            {"role": "system", "content": "here is CSV file with league codes and names: " + league_csv + ". now, read this sentence and get the league code from the previous CSV data: \"" + user_input + "\". only return the league code in json format, like this \{code\: [CODE]\}, avoid any other comment"}
        ]

        payload = {
            'model': 'gpt-4',
            'messages': messages,
            'max_tokens': 20,
            'temperature': 0,
        }

        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        league_name = result['choices'][0]['message']['content'].strip()

        # Regular expression to match the code value
        match = re.search(r'"code":\s*"([^"]+)"', league_name)

        # Check if a match is found and extract the code
        if match:
            code = match.group(1)

        return code

    except Exception as e:
        print(f"Error extracting league name: {e}")
        return None


# Function to extract player name using OpenAI
def extract_player_name(user_input):
    try:
        if not OPENAI_API_KEY:
            raise Exception("OpenAI API key is not set")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_API_KEY}',
        }

        messages = [
            {"role": "system", "content": "Extract the player name from the user's message and return only the player's name."},
            {"role": "user", "content": user_input}
        ]

        payload = {
            'model': 'gpt-3.5-turbo',
            'messages': messages,
            'max_tokens': 10,
            'temperature': 0,
        }

        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        player_name = result['choices'][0]['message']['content'].strip()

        return player_name

    except Exception as e:
        print(f"Error extracting player name: {e}")
        return None

def get_league_winners(league_code):
    url = f'https://api.football-data.org/v4/competitions/{league_code}'

    headers = {
        'X-Auth-Token': FOOTBALL_ORG_API_KEY
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {'error': f"API request failed with status code {response.status_code}: {response.text}"}

    data = response.json()
    seasons = data.get('seasons', [])

    # Filter seasons with a winner and get the last 10
    seasons_with_winner = [season for season in seasons if season.get('winner') is not None]
    last_10_seasons = seasons_with_winner[:10]

    if not last_10_seasons:
        return {'error': f"No winners found for the last 10 seasons of {data.get('name')}."}

    # Build a list of season data
    season_data = []
    for season in last_10_seasons:
        winner = season['winner']
        winner_name = winner.get('name', 'Unknown') if winner else 'Unknown'
        start_date = season.get('startDate', 'Unknown')
        end_date = season.get('endDate', 'Unknown')
        season_data.append({
            'start_date': start_date,
            'end_date': end_date,
            'winner': winner_name
        })

    # Return the data as a dictionary
    return {
        'league_name': data.get('name'),
        'seasons': season_data
    }
     
# Function to generate top 5 goal scorers graph
def generate_top_scorers_graph():
    try:
        if not FOOTBALL_ORG_API_KEY:
            raise Exception("Football API key is not set")

        headers = {
            'X-Auth-Token': FOOTBALL_ORG_API_KEY
        }

        # Fetch top scorers
        url = f"{FOOTBALL_ORG_API_URL}/competitions/PL/scorers"
        params = {'limit': 5}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        scorers = data['scorers']

        players = [scorer['player']['name'] for scorer in scorers]
        goals = [scorer['goals'] for scorer in scorers]

        # Generate bar chart
        plt.figure(figsize=(10, 6))
        plt.bar(players, goals, color='skyblue')
        plt.xlabel('Players')
        plt.ylabel('Goals')
        plt.title('Top 5 Goal Scorers')
        plt.tight_layout()

        # Save plot to a bytes buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()

        # Encode image to base64
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return image_base64

    except Exception as e:
        print(f"Error generating graph: {e}")
        return None

# Default assistant response using OpenAI
def get_default_response(user_message):
    try:
        if not OPENAI_API_KEY:
            raise Exception("OpenAI API key is not set")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_API_KEY}',
        }

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ]

        payload = {
            'model': 'gpt-3.5-turbo',
            'messages': messages,
            'max_tokens': 150,
            'temperature': 0.7,
        }

        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        assistant_reply = result['choices'][0]['message']['content'].strip()
        return assistant_reply

    except Exception as e:
        print(f"Error getting default response: {e}")
        return "Sorry, I couldn't process your request."

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'No message provided.'}), 400

        # Intent: Show me the stats for [League Name]
        if 'show me the stats for' in user_message.lower():
            league_code = get_league_code(user_message)
            if not league_code:
                reply = f"League not found."
                return jsonify({'reply': reply})

            # Call the get_league_winners function
            result = get_league_winners(league_code)

            if 'error' in result:
                return jsonify({'reply': result['error']})

            # Return the data as a table_data key
            return jsonify({
                'table_data': {
                    'league_name': result['league_name'],
                    'seasons': result['seasons']
                }
            })

        # Intent 2: Show me a graph of the top 5 goal scorers this season
        elif 'show me a graph of the top 5 goal scorers' in user_message.lower():
            image_base64 = generate_top_scorers_graph()
            if not image_base64:
                reply = "Sorry, I couldn't generate the graph."
                return jsonify({'reply': reply})

            return jsonify({'image': image_base64})

        # Default response
        else:
            assistant_reply = get_default_response(user_message)
            return jsonify({'reply': assistant_reply})

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'error': 'An error occurred processing your request.'}), 500

if __name__ == '__main__':
    app.run(port=3000)
