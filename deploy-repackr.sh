#!/bin/bash

# Script to deploy RePackr to GitHub Pages
echo "Deploying RePackr to GitHub Pages..."

# Check if we're in the right directory
if [ ! -d "repackr" ]; then
    echo "Error: repackr directory not found. Please run this script from the jaredescott.github.io directory."
    exit 1
fi

# Add the repackr directory to git
git add repackr/

# Commit the changes
git commit -m "Add RePackr travel packing planner app"

# Push to GitHub
echo "Pushing to GitHub..."
git push origin master

echo "Deployment complete! The RePackr app should be available at https://jaredescott.github.io/repackr/ in a few minutes."
