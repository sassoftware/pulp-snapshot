import logging
import os
from ConfigParser import SafeConfigParser
from gettext import gettext as _


_LOG = logging.getLogger(__name__)

REQUIRED_CONFIG_KEYS = ()
OPTIONAL_CONFIG_KEYS = ()


def load_config(config_file_path):
    """
    Load and return a config parser for the given configuration file path.

    :param config_file_path: full path to the configuration file
    :type  config_file_path: str
    :return: Parser representing the parsed configuration file
    :rtype:  SafeConfigParser
    """
    _LOG.debug('Loading configuration file: %s' % config_file_path)

    config = SafeConfigParser()

    if os.access(config_file_path, os.F_OK | os.R_OK):
        config.read(config_file_path)
    else:
        _LOG.warning(_('Could not load config file: %(f)s') %
                     {'f': config_file_path})

    return config


def validate_config(repo, config, config_conduit):
    """
    Validate the prospective configuration instance for the the give repository.

    :param repo: repository to validate the config for
    :type  repo: pulp.plugins.model.Repository
    :param config: configuration instance to validate
    :type  config: pulp.plugins.config.PluginCallConfiguration
    :param config_conduit: conduit providing access to relevant Pulp
    functionality
    :type  config_conduit: pulp.plugins.conduits.repo_config.RepoConfigConduit
    :return: tuple of (bool, str) stating that the configuration is valid
    or not and why
    :rtype:  tuple of (bool, str or None)
    """
    # squish it into a dictionary so we can manipulate it
    if not isinstance(config, dict):
        config = config.flatten()
    error_messages = []

    configured_keys = set(config)
    required_keys = set(REQUIRED_CONFIG_KEYS)
    supported_keys = set(REQUIRED_CONFIG_KEYS + OPTIONAL_CONFIG_KEYS)

    # check for any required options that are missing
    missing_keys = required_keys - configured_keys
    msg = _('Configuration key [%(k)s] is required, but was not provided')
    for key in sorted(missing_keys):
        error_messages.append(msg % {'k': key})

    # check for unsupported configuration options
    extraneous_keys = configured_keys - supported_keys
    msg = _('Configuration key [%(k)s] is not supported')
    for key in extraneous_keys:
        error_messages.append(msg % {'k': key})

    # when adding validation methods, make sure to register them here
    # yes, the individual sections are in alphabetical oder
    configured_key_validation_methods = {
    }

    # iterate through the options that have validation methods and validate them
    for key, validation_method in configured_key_validation_methods.items():

        if key not in configured_keys:
            continue

        validation_method(config[key], error_messages)

    # if we have errors, log them, and return False with a concatenated
    # error message
    if error_messages:

        for msg in error_messages:
            _LOG.error(msg)

        return False, '\n'.join(error_messages)

    return True, None
