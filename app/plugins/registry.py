PLUGINS = {}

def register(name, plugin):
    PLUGINS[name] = plugin

def get(name):
    return PLUGINS.get(name)
