from flask import Flask, jsonify, request
import pandas as pd
import threading
import os
from datetime import datetime

app = Flask(__name__)
LOCK = threading.Lock()

def get_csv_path(category):
    return os.path.join(os.path.dirname(__file__), f"{category}.csv")

def process_get(category):
    csv_path = get_csv_path(category)
    with LOCK:
        df = pd.read_csv(csv_path)

        # Ensure columns exist
        df['status'] = df.get('status', '').fillna('').astype(str)
        if 'last_updated' not in df.columns:
            df['last_updated'] = ''

        # Find next item with empty status
        pending = df[df['status'].str.strip() == '']

        if pending.empty:
            return jsonify({'message': f'No pending {category} found.'}), 404

        item = pending.iloc[0]
        idx = item.name

        # Mark as working
        df.at[idx, 'status'] = 'working'
        df.at[idx, 'last_updated'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        df.to_csv(csv_path, index=False)

        return jsonify({'title': item['title']})

def process_post(category, title):
    csv_path = get_csv_path(category)
    with LOCK:
        df = pd.read_csv(csv_path)

        df['status'] = df.get('status', '').fillna('').astype(str)
        if 'last_updated' not in df.columns:
            df['last_updated'] = ''

        matched = df['title'].str.strip().str.lower() == title.strip().lower()

        if not matched.any():
            return jsonify({'message': f'{category.capitalize()} not found.'}), 404

        df.loc[matched, 'status'] = 'done'
        df.to_csv(csv_path, index=False)

        return jsonify({'message': f'"{title}" marked as done in {category}.'})

# Routes for movies
@app.route('/movie', methods=['GET'])
def get_movie():
    return process_get('movies')

@app.route('/movie/<title>', methods=['POST'])
def post_movie(title):
    return process_post('movies', title)

# Routes for tvshows
@app.route('/tvshow', methods=['GET'])
def get_tvshow():
    return process_get('tvshows')

@app.route('/tvshow/<title>', methods=['POST'])
def post_tvshow(title):
    return process_post('tvshows', title)

# Routes for series
@app.route('/series', methods=['GET'])
def get_series():
    return process_get('series')

@app.route('/series/<title>', methods=['POST'])
def post_series(title):
    return process_post('series', title)

if __name__ == '__main__':
    app.run(debug=True)