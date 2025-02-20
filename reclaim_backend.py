from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

API_URL = "https://api.app.reclaim.ai/api/tasks"

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    token = request.headers.get('Authorization').replace('Bearer ', '')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    if request.method == 'GET':
        params = {'status': 'NEW,SCHEDULED,IN_PROGRESS,COMPLETE', 'instances': 'true'}
        response = requests.get(API_URL, headers=headers, params=params)
        return jsonify(response.json())
    
    elif request.method == 'POST':
        data = request.json
        response = requests.post(API_URL, headers=headers, json=data)
        return jsonify(response.json())

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def handle_task(task_id):
    token = request.headers.get('Authorization').replace('Bearer ', '')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    response = requests.delete(f"{API_URL}/{task_id}", headers=headers)
    return '', response.status_code

if __name__ == '__main__':
    app.run(port=5000) 