from database import DatabaseQuery
from discord.ext import commands, tasks
from discord import app_commands, Embed
import aiohttp, asyncio, time, datetime


class bs_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.headers = None
        self.db = DatabaseQuery()

        self.active = True

    async def init_bot(self):
        if self.active:
            self.update_clubs_joins_loop.start()
            await asyncio.sleep(60 * 4)
            self.check_players_club_ligue.start()

    def get_week_number_since_epoch(self):
        return int(int(time.time()) / 604800)

    def get_day_number_since_epoch(self):
        return int(int(time.time()) / 86400)

    def get_current_utc_date(self):
        current_utc_date = datetime.datetime.utcnow().strftime('%Y%m%d')
        return current_utc_date

    @tasks.loop(minutes=10)
    async def update_clubs_joins_loop(self):
        tasks = [self.update_joined_member_in_club(club_id) for club_id in self.db.get_all_club_ids()]
        await asyncio.gather(*tasks)

    @tasks.loop(minutes=30)
    async def check_players_club_ligue(self):
        if self.get_week_number_since_epoch() % 2 != 0:  # only try on club ligue weeks
            return

        current_day_id = self.get_day_number_since_epoch()
        current_week = self.get_week_number_since_epoch()
        current_day = self.get_current_utc_date()
        tasks = [self.update_player_ligue_participation(member_id, current_week, current_day_id, current_day) for
                 member_id in
                 self.db.get_all_clubs_members()]
        await asyncio.gather(*tasks)

    async def get_api_response(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return "NotFound"
                else:
                    print(response)
                    print(f"Error: {response.status}")
                    return

    def formated_id(self, str_id):
        return str_id[1:] if str_id[0] == '#' else str_id

    async def get_infos_embed(self, club_id, members):
        club_infos = await self.get_api_response(f"https://api.brawlstars.com/v1/clubs/%23{club_id}")
        if club_infos == "NotFound" or not club_infos:
            return
        club_name = club_infos["name"]
        e = Embed(title=f"{club_name} | {club_id}")
        e.add_field(name="Club Ligue Tickets:", value="Day - Week - All")
        members_infos = {}
        for member_id in members:
            # 0: in_club, 1: tickets_played_all, 2: tickets_played_week, 3: tickets_week_id, 4: tickets_played_today, 5: tickets_day_id, 6: last_checked_combat, 7: joins, 8: join_date, 9: in_club
            member_infos = self.db.retrive_member_ligue_infos(member_id)
            member_infos += self.db.retrive_member_join_infos(member_id)
            members_infos[member_id] = member_infos

        #sort by most tickets played today:
        sorted_members = sorted(members_infos, key=lambda x: x[4], reverse=True)

        names = await self.fetch_names_for_ids(sorted_members)

        for i in range(0, len(sorted_members), 2):
            member_infos_1 = members_infos[sorted_members[i]]
            member1_formated_infos = f"**{names[i]}**: {member_infos_1[4]} - {member_infos_1[2]} - {member_infos_1[1]} | Joins: {member_infos_1[7]}\n"
            member2_formated_infos = ""

            if i + 1 < len(sorted_members):
                member_infos_2 = members_infos[sorted_members[i + 1]]
                member2_formated_infos = f"**{names[i + 1]}**: {member_infos_2[4]} - {member_infos_2[2]} - {member_infos_2[1]} | Joins: {member_infos_2[7]}\n"

            e.add_field(name=member1_formated_infos, value=member2_formated_infos)

        return e

    @app_commands.command(name="check", description="Check a club activity")
    async def check(self, interaction, club_id: str = ""):
        await interaction.response.defer(thinking=False, ephemeral=True)

        if not club_id:
            user_club = self.db.get_discord_user_club(interaction.user.id)
            if not user_club:
                await interaction.followup.send("You are not following any club, enter an id with the command.")
                return
            club_id = user_club[0]

        club_id = self.formated_id(club_id)
        if self.db.is_club_in_database(club_id):
            if self.db.get_discord_user_club(interaction.user.id):
                self.db.udate_discord_user_club(interaction.user.id, club_id)
            else:
                self.db.register_discord_user(interaction.user.id, club_id)

            members = self.db.retrive_club_members(club_id)
            e = await self.get_infos_embed(club_id, members)
            await interaction.followup.send("Here is your infos", embed=e)
        else:
            await interaction.followup.send("Club not registred.")

    @app_commands.command(name="moderate", description="Start following a club activity")
    async def moderate(self, interaction, club_id: str):
        await interaction.response.defer(thinking=False, ephemeral=True)

        club_id = self.formated_id(club_id)
        if self.db.is_club_in_database(club_id):
            await interaction.followup.send("This club is already registred.")
            return

        club_infos = await self.get_api_response(f"https://api.brawlstars.com/v1/clubs/%23{club_id}")
        if not club_infos:
            await interaction.followup.send("An error occured on our side, try again later...")
            return

        if club_infos == "NotFound":
            await interaction.followup.send("This club does not exist...")
            return

        self.db.register_club(club_id)
        for member in club_infos["members"]:
            self.db.register_member(club_id, self.formated_id(member["tag"]))

        if self.db.get_discord_user_club(interaction.user.id):
            self.db.udate_discord_user_club(interaction.user.id, club_id)
        else:
            self.db.register_discord_user(interaction.user.id, club_id)

        await interaction.followup.send(f"Starting the moderation of {club_infos['name']}")

    async def update_joined_member_in_club(self, club_id):
        club_infos = await self.get_api_response(f"https://api.brawlstars.com/v1/clubs/%23{club_id}")

        if club_infos and club_infos != "NotFound":
            actual_members = [self.formated_id(member["tag"]) for member in club_infos["members"]]
            last_saved_members = self.db.retrive_club_members(club_id)

            if actual_members == last_saved_members:
                return

            for actual_member_id in actual_members:
                if actual_member_id not in last_saved_members:
                    self.db.register_member(club_id, actual_member_id)

            for last_saved_member_id in last_saved_members:
                if last_saved_member_id not in actual_members:
                    self.db.on_member_quit(club_id, last_saved_member_id)

    async def fetch_names_for_ids(self, member_ids):
        tasks = []

        for member_id in member_ids:
            # Construct the API URL for each member
            api_url = f"https://api.brawlstars.com/v1/players/%23{member_id}"
            tasks.append(self.get_api_response(api_url))

        responses = await asyncio.gather(*tasks)

        # Process the responses
        names = []
        for response in responses:
            if response and response != "NotFound":
                names.append(response.get("name", "NotFound"))
            else:
                names.append("NotFound")

        return names

    async def update_player_ligue_participation(self, member_id, current_week, current_day_id, current_day):
        # 0: in_club, 1: tickets_played_all, 2: tickets_played_week, 3: tickets_week_id, 4: tickets_played_today, 5: tickets_day_id, 6: last_checked_combat
        member_infos = self.db.retrive_member_ligue_infos(member_id)
        in_club = member_infos[0]
        tickets_played_all = member_infos[1]
        tickets_played_week = member_infos[2]
        tickets_week_id = member_infos[3]
        tickets_played_today = member_infos[4]
        tickets_day_id = member_infos[5]
        last_checked_combat = member_infos[6]

        if not in_club:
            return

        if tickets_week_id == current_week:
            if tickets_played_week == 14:
                return
        else:
            tickets_week_id = current_week
            tickets_played_week = 0

        if tickets_day_id != current_day_id:
            tickets_played_today = 0
            tickets_day_id = current_day_id

        battle_log = await self.get_api_response(f"https://api.brawlstars.com/v1/players/%23{member_id}/battlelog")
        if not battle_log or battle_log == "NotFound":
            return

        for battle in reversed(battle_log["items"]):
            if battle["battleTime"] > last_checked_combat and battle["battleTime"].startswith(current_day):
                if trophy_change := battle["battle"].get("trophyChange", False):
                    if trophy_change > 0:
                        if len(team := battle["battle"].get("teams", [[]])[0]) > 2 and team[0]["brawler"][
                            "trophies"] < 20:
                            last_checked_combat = battle["battleTime"]
                            # Todo add trophy cont
                            if battle["battle"]["type"] == "teamRanked":
                                tickets = 2
                            elif battle["battle"]["type"] == "ranked":
                                tickets = 1
                            else:
                                print(battle["battle"]["type"])
                                continue
                            tickets_played_all += tickets
                            tickets_played_week += tickets
                            tickets_played_today += tickets

        self.db.update_member_ligue_infos(member_id, tickets_played_all, tickets_played_week, tickets_week_id,
                                          tickets_played_today, tickets_day_id, last_checked_combat)
