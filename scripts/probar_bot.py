import requests

BASE_URL = "http://localhost:8000"

def chat(org_id, user_id, mensaje):
    respuesta = requests.post(
        f"{BASE_URL}/chat",
        params={
            "org_id": org_id,
            "user_id": user_id,
            "mensaje": mensaje
        }
    )
    data = respuesta.json()
    print(f"\nUsuario: {mensaje}")
    print(f"Bot ({org_id}): {data['respuesta']}")
    print("-" * 50)

if __name__ == "__main__":
    print("=== TEST: Reintegro ===")
    chat("org_1", "user_123", "Quiero un reintegro de $50000")

    print("\n=== TEST: Fuera de dominio ===")
    chat("org_1", "user_123", "¿Cuál es tu color favorito?")

    print("\n=== TEST: Spam operador ===")
    chat("org_1", "user_123", "operador operador operador")

    print("\n=== TEST: Org inválida ===")
    chat("org_fake", "user_123", "Hola")

    print("\n=== TEST: Límite excedido ===")
    chat("org_1", "user_123", "Quiero reintegro de $200000")