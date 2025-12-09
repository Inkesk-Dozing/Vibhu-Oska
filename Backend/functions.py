

#this file contains the main functions for Vibhu-Oska package

class Introduction:
    def __init__(self,name,age,location):
        self.name = name
        self.age = age
        self.location = location
        
    def greet(self,name):
        return f"Hello{name}! My to the Vibhu-Oska. How can I assist you today?"