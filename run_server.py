from backend.app import create_app

# Create the Flask app when this module is imported (required by gunicorn)
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=800)
