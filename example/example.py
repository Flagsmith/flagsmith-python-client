import json

from flagsmith import Flagsmith

api_key = input('Please provide an environment api key: ')

flagsmith = Flagsmith(environment_id=api_key)

identifier = input('Please provide an example identity: ')
feature_name = input('Please provide an example feature name: ')

print_get_flags = input('Print result of get_flags for environment? (y/n) ')
if print_get_flags.lower() == 'y':
    print(json.dumps(flagsmith.get_flags(), indent=2))

print_get_flags_with_identity = input('Print result of get_flags with identity? (y/n) ')
if print_get_flags_with_identity.lower() == 'y':
    print(json.dumps(flagsmith.get_flags(identifier), indent=2))

print_get_flags_for_user = input('Print result of get_flags_for_user? (y/n) ')
if print_get_flags_for_user.lower() == 'y':
    print(json.dumps(flagsmith.get_flags_for_user(identifier), indent=2))

print_get_value_of_feature_for_environment = input('Print result of get_value for environment? (y/n) ')
if print_get_value_of_feature_for_environment.lower() == 'y':
    print(flagsmith.get_value(feature_name))

print_get_value_of_feature_for_environment = input('Print result of get_value for identity? (y/n) ')
if print_get_value_of_feature_for_environment.lower() == 'y':
    print(flagsmith.get_value(feature_name, identity=identifier))

print_result_of_has_feature = input('Print result of has feature? (y/n) ')
if print_result_of_has_feature.lower() == 'y':
    print(flagsmith.has_feature(feature_name))

print_result_of_feature_enabled_for_environment = input('Print result of feature_enabled for environment? (y/n) ')
if print_result_of_feature_enabled_for_environment.lower() == 'y':
    print(flagsmith.feature_enabled(feature_name))

print_result_of_feature_enabled_for_identity = input('Print result of feature_enabled for identity? (y/n) ')
if print_result_of_feature_enabled_for_identity.lower() == 'y':
    print(flagsmith.feature_enabled(feature_name, identity=identifier))

set_trait = input('Would you like to test traits? (y/n) ')
if set_trait.lower() == 'y':
    trait_key = input('Trait key: ')
    trait_value = input('Trait value: ')
    flagsmith.set_trait(trait_key, trait_value, identifier)
    print('Trait set successfully')
    print('Result from get_trait is %s' % flagsmith.get_trait(trait_key, identifier))
