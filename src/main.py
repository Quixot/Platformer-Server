import asyncio
import json
import random
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        player_id = len(self.active_connections) + 1
        self.active_connections[websocket] = {"player_id": player_id, "x": 50, "y": 500, "direction": "right", "speed_x": 0, "speed_y": 0, "on_ground": False}
        return player_id

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    player_id = await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Обработка логики игрока
            player = manager.active_connections[websocket]
            if message["action"] == "move_left":
                player["speed_x"] = -5
                player["direction"] = "left"
            elif message["action"] == "move_right":
                player["speed_x"] = 5
                player["direction"] = "right"
            elif message["action"] == "jump" and player["on_ground"]:
                player["speed_y"] = -15
                player["on_ground"] = False
            elif message["action"] == "stop":
                player["speed_x"] = 0

            # Обновление состояния игрока
            player["x"] += player["speed_x"]
            player["y"] += player["speed_y"]

            # Гравитация
            if not player["on_ground"]:
                player["speed_y"] += 0.5
            if player["y"] > 500:
                player["y"] = 500
                player["on_ground"] = True
                player["speed_y"] = 0

            # Отправка обновленного состояния всем клиентам
            await manager.broadcast({"action": "update", "players": list(manager.active_connections.values())})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({"action": "disconnect", "player_id": player_id})




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
