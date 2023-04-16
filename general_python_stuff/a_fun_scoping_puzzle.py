"""What will this print?"""

def get_callbacks():
    callbacks = []
    for name in "Bob", "Joe", "Sue":
        def callback(name=name):
            print(name)
        callbacks.append(callback)
    return callbacks

for cb in get_callbacks():
    cb()
