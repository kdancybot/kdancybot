from datetime import datetime, timedelta
import Message


class Timer:
    def __init__(self, hours=0, minutes=0, seconds=0):
        self.current_time = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        self.resume_time = datetime.now()
        self.paused = True

    def resume(self, message: Message.Message):
        if self.paused and (
            message.user == message.channel or message.tags.get("moderator")
        ):
            self.resume_time = datetime.now()
            self.paused = False
            return f"Timer is now running. {self.timer()}"
        return "dogQ"

    def pause(self, message: Message.Message):
        if not self.paused and (
            message.user == message.channel or message.tags.get("moderator")
        ):
            self.current_time += datetime.now() - self.resume_time
            self.paused = True
            return f"Timer is now paused. {self.timer()}"
        return "dogQ"

    def timer(self, message):
        td = self.current_time
        if self.paused:
            td += datetime.now() - self.resume_time
        hours, minutes, seconds = (
            td.seconds // 3600,
            td.seconds // 60 % 60,
            int(td.seconds % 60),
        )
        return f"Current time: {hours} hours, {minutes} minutes and {seconds} seconds"
