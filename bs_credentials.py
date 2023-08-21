import os

import aiohttp, asyncio

class BrawlStarsSession:
    def __init__(self, public_ip):
        self.public_ip = public_ip
        self.session = aiohttp.ClientSession()
        self.cookie = None

        # Set the login endpoint URL
        self.login_url = "https://developer.brawlstars.com/api/login"
        self.login_payload = {
            "email": os.environ["email"],
            "password": os.environ["password"]
        }
        self.login_headers = {
            "Content-Type": "application/json",
            "Referer": "https://developer.brawlstars.com/",
            "Origin": "https://developer.brawlstars.com"
        }

        # Set the create endpoint URL
        self.create_url = "https://developer.brawlstars.com/api/apikey/create"
        self.create_payload = {
            "name": f"BST",
            "description": "Discord bot that tracks players activity and display stats !",
            "cidrRanges": [public_ip],
            "scopes": None
        }

        # Set the delete endpoint URL
        self.delete_url = "https://developer.brawlstars.com/api/apikey/revoke"


    async def login(self):
        async with self.session.post(self.login_url, json=self.login_payload, headers=self.login_headers) as login_response:
            if login_response.status == 200:
                print("Login !")
                # Retrieve the cookie from the response headers
                self.cookie = login_response.cookies.get("session")
            else:
                print(login_response.content)

    async def get_api_key(self):
        self.create_headers = {
            "Content-Type": "application/json",
            "Cookie": f"session={self.cookie}",
            "Referer": "https://developer.brawlstars.com/",
            "Origin": "https://developer.brawlstars.com"
        }
        async with self.session.post(self.create_url, json=self.create_payload, headers=self.create_headers) as api_response:
            # Process the API response as needed
            if api_response.status == 200:
                response_json = await api_response.json()
                key_info = response_json.get("key")
                return key_info
            else:
                print("failed getting key")
                print(api_response.status)
                print(api_response)
                print(api_response.reason)
                print(api_response.content)
                return None

    async def del_api_key(self, key_id):
        self.delete_payload = {"id": key_id}
        async with self.session.post(self.delete_url, json=self.delete_payload, headers=self.create_headers) as api_response:
            pass
