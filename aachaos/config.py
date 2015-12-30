"""Interface for the configuration file."""
import os
import configparser


class ConfigurationError(Exception): pass


class Settings(configparser.ConfigParser):

    xdg_config_default = os.path.expanduser('~/.config')
    xdg_config = os.getenv('XDG_CONFIG_HOME', xdg_config_default)

    ini_path = os.path.join(xdg_config, __package__, 'config.ini')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read(self.ini_path)

    def get(self, section, option, *args, **kwargs):
        # Overriding __getitem__ on the Section proxy didn't appear to
        # work, so this is the incomplete workaround.
        string = super().get(section, option, *args, **kwargs)
        if section == 'Path':
            string = os.path.expandvars(os.path.expanduser(string))
            if os.path.abspath(string) != string:
                raise ConfigurationError(
                    "{} path must be absolute".format(option)
                )
        return string

settings = Settings()
