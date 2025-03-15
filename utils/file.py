import openai

def upload_file(path):
    file = openai.files.create(
        file=open(path, "rb"),
        purpose="assistants"
    )
    print(f" File uploaded: {file.id}")
    return file.id
