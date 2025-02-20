from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)

API_URL = "https://api.app.reclaim.ai/api/tasks"
DEPENDENCIES_FILE = Path("../reclaim_dependencies.json")

# Load or initialize dependencies
if DEPENDENCIES_FILE.exists():
    with open(DEPENDENCIES_FILE) as f:
        dependencies = json.load(f)
else:
    dependencies = {}
    # Create the file
    with open(DEPENDENCIES_FILE, 'w') as f:
        json.dump({}, f)

def save_dependencies():
    with open(DEPENDENCIES_FILE, 'w') as f:
        json.dump(dependencies, f)

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
        tasks = response.json()
        # Add dependency info to tasks
        for task in tasks:
            # Only add dependencies if they exist in our local storage
            task_id = str(task['id'])
            if task_id in dependencies:
                task['dependencies'] = dependencies[task_id]
            else:
                task['dependencies'] = []
        return jsonify(tasks)
    
    elif request.method == 'POST':
        data = request.json.copy()  # Copy to modify
        # Store dependencies separately
        deps = data.pop('dependencies', [])
        
        # If task has dependencies, set snoozeUntil to latest due date of dependencies
        if deps:
            # First get all tasks to find dependencies
            tasks_response = requests.get(API_URL, headers=headers)
            all_tasks = tasks_response.json()
            dep_tasks = [t for t in all_tasks if str(t['id']) in deps]
            latest_due = max((t['due'] for t in dep_tasks if t.get('due')), default=None)
            if latest_due:
                data['snoozeUntil'] = latest_due
        
        response = requests.post(API_URL, headers=headers, json=data)
        if response.ok:
            task_id = str(response.json()['id'])
            dependencies[task_id] = deps
            save_dependencies()
        return jsonify(response.json())

@app.route('/api/dependencies/<task_id>', methods=['GET', 'PUT'])
def handle_dependencies(task_id):
    if request.method == 'GET':
        return jsonify(dependencies.get(task_id, []))
    elif request.method == 'PUT':
        dependencies[task_id] = request.json
        save_dependencies()
        return '', 204

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def handle_task(task_id):
    token = request.headers.get('Authorization').replace('Bearer ', '')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    response = requests.delete(f"{API_URL}/{task_id}", headers=headers)
    if response.ok:
        dependencies.pop(str(task_id), None)
        save_dependencies()
    return '', response.status_code

if __name__ == '__main__':
    app.run(port=5000) 