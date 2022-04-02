from fastapi import FastAPI

app = FastAPI()  # app 实例化位于所有导入之前


@app.get('/')
async def home():
    return {'message': 'hello world'}
