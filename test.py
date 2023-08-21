import time


def get_week_number_since_epoch(self):
    return int(int(time.time()) / 604800)


# Example usage
current_unix_time = int(time.time())  # Convert to integer
weeks_since_epoch = get_week_number_since_epoch(current_unix_time)
print("Weeks Since 1970:", weeks_since_epoch)
