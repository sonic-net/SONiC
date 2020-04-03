# Enhancement for Media Settings Lookup Key
## Introduction
The SONiC optical media transceiver daemon, xcvrd, is responsible for obtaining certain settings that are dependent on the type of transceiver installed, which port it is installed in, and on which platform it is running.  An example of such a setting is NPU port preemphasis.  
This is done using a JSON file, media_settings.json, provided with each platform, to describe a mapping from certain transceiver properties to media settings.  Xcvrd builds pair of keys, based on the type of the inserted transceiver, and for each key, attempts to find an entry in a dictionary created from media_settings.json for that key; if an entry is found, the settings corresponding to that key are used.
## Current implementation
In xcvrd, the function get_media_settings_key() is used to form a list of two strings.  These strings are used as lookup keys for the dictionary created from the file media_settings.json.  
The current implementation of get_media_settings_key() constructs two keys, as follows:
- the first key is of the form _manufacturer_-_partnumber_, where _manufacturer_ and _partnumber_ are the name of the transceiver manufacturer and the manufacturer's part number, respectively, which are read from the transceiver EEPROM, and
- the second key if of the form _type_-_compliancecode_-_length_, where _type_ is the transceiver type (e.g. SFP, SFP28, QSFP, etc.), _compliancecode_ is the physical layer standard (e.g. 10GBASE-SR, 40GBASE-CR4), and _length_ is the length of the attached cable, if applicable.
# Enhancement
Xcvrd shall be modified such that it will check for the presence of a platform-dependent plugin, which shall contain an implementation of the function get_media_settings_key().  Xcvrd shall check for the presence of this plugin, and, if found, use it in preference to the built-in function get_media_settings_key().  
The signature of the plugin get_media_settings_key() function must be the same as that of the built-in function.
The form of the return value of the plugin function get_media_settings_key() must match that of the built-in get_media_settings_key(), namely, a list of two strings.  However, the plugin function is free to choose how those strings are constructed; it can use any information about the transceiver to construct its keys.  
The function which uses the keys, and attempts the lookup in media_settings.json, is content-agnostic; it expects only a list of 2 strings, what strings represent is not relevant.
# Impact
- At startup, check for presence of media_settings_key plugin; if a plugin is found, import it
- Create a wrapper function for get_media_settings_key, that checks if a plugin was imported, and if yes, calls the function get_media_settings_key() in the plugin; if a plugin was not imported, call the current, built-in function get_media_settings_key()
- Change the current call to get_media_settings_key() to call the above wrapper function instead
# Backward compatibility
The media settings plugin is optional, and the enhanced code will fall back to use the current built-in get_media_settings_key() function if a plugin is not found.  Thus, the enhanced xcvrd will be able to run on existing platforms, which to not currently have a media settings plugin, and backward compatibility is assured.
