#set up testing of actual vs expected results
#get epoch state from filtered logs for each query response epoch
#get theh query and test it through the epoch state 
import re
import ast


def get_uuid_epoch(file_name: str):
    """
    Parse the query response log file to extract UUID and Epoch.

    :param file_name: Name of the query response log file to parse.
    :return: List of tuples containing UUID and Epoch values.
    """
    uuid_epoch_list = []

    # Open and process the log file
    with open(file_name, "r") as log_file:
        for line in log_file:
            # Check if the line contains a UUID and Epoch
            if "Received response for query uuid:" in line:
                uuid_match = re.search(r"uuid: (\S+)", line)
                if uuid_match:
                    uuid = uuid_match.group(1)
            elif "'epoch':" in line:
                epoch_match = re.search(r"'epoch': (\d+)", line)
                if epoch_match:
                    epoch = int(epoch_match.group(1))
                    uuid_epoch_list.append((uuid, epoch))

    return uuid_epoch_list


def collect_epoch_state(file_name: str, epoch: int):
    epoch_states = {}

    # Open and process the filtered log file
    with open(file_name, "r") as log_file:

        for line in log_file:
            # Check if line contains epoch state information (for any epoch up to target)
            if "State at Epoch |||:" in line:
                current_epoch = int(re.search(r"State at Epoch \|\|\|: (\d+):", line).group(1))

                if 1 <= current_epoch <= epoch:
                    state_match = re.search(r"State at Epoch \|\|\|: \d+: (.+)", line)
                    if state_match:
                        # Use `ast.literal_eval` to safely parse the dictionary-like string
                        states_str = state_match.group(1)
                        parsed_states = ast.literal_eval(states_str)

                        # Merge the new states with existing ones
                        for key, value in parsed_states.items():
                            if key in epoch_states:
                                # If key exists, update only if new value is different
                                if value != epoch_states[key]:
                                    epoch_states[key] = value
                            else:
                                # Add new key-value pair
                                epoch_states[key] = value

    return epoch_states

#verify answer
# Example usage
uuid_epoch_data = get_uuid_epoch("query_response.log")
# print(len(uuid_epoch_data))
epoch_states = collect_epoch_state("/home/mitalipatil/PycharmProjects/styx/filtered-logs.log", epoch=137)
# print(uuid_epoch_data)
print(epoch_states)


# # tests/test_querystate_service.py
#
# import unittest
# from unittest.mock import AsyncMock, patch
#
# from querystate.querystate_service import QueryStateService
#
#
# class TestQueryStateService(unittest.IsolatedAsyncioTestCase):
#
#     async def asyncSetUp(self):
#         self.service = QueryStateService()
#         self.service.latest_epoch_count = 137
#         self.service.state_store = collect_epoch_state("/home/mitalipatil/PycharmProjects/styx/filtered-logs.log", epoch=137)
#         # print(self.service.state_store)
#
#     async def test_get_query_state_response_get_state(self):
#         query = {'type': 'GET_STATE', 'uuid': '12345'}
#         expected_response = {
#             'uuid': '12345',
#             'epoch': 42,
#             'state': self.service.state_store
#         }
#
#         response = await self.service.get_query_state_response(query)
#         self.assertEqual(response, expected_response)
#
#     async def test_get_query_state_response_get_operator_state(self):
#         query = {'type': 'GET_OPERATOR_STATE', 'uuid': '12345', 'operator': 'operator1'}
#         expected_response = {
#             'uuid': '12345',
#             'epoch': 42,
#             'operator_state': {1: 'value1', 2: 'value2', 3: 'value3'}
#         }
#
#         response = await self.service.get_query_state_response(query)
#         self.assertEqual(response, expected_response)
#
#     async def test_get_query_state_response_get_operator_partition_state(self):
#         query = {'type': 'GET_OPERATOR_PARTITION_STATE', 'uuid': '9f00a4dc-ca15-428b-bee0-2167c555262f', 'operator': 'stock', 'partition': 1}
#         expected_response = {
#             'uuid': '9f00a4dc-ca15-428b-bee0-2167c555262f',
#             'epoch': 137,
#             'operator_partition_state': {'1': {'stock': 10000, 'price': 1}, '5': {'stock': 10000, 'price': 1}, '9': {'stock': 10000, 'price': 1}, '13': {'stock': 10000, 'price': 1}, '17': {'stock': 10000, 'price': 1}, '21': {'stock': 9999, 'price': 1}, '25': {'stock': 10000, 'price': 1}, '29': {'stock': 10000, 'price': 1}, '33': {'stock': 9999, 'price': 1}, '37': {'stock': 10000, 'price': 1}, '41': {'stock': 10000, 'price': 1}, '45': {'stock': 9999, 'price': 1}, '49': {'stock': 10000, 'price': 1}, '53': {'stock': 9999, 'price': 1}, '57': {'stock': 10000, 'price': 1}, '61': {'stock': 9999, 'price': 1}, '65': {'stock': 10000, 'price': 1}, '69': {'stock': 10000, 'price': 1}, '73': {'stock': 10000, 'price': 1}, '77': {'stock': 10000, 'price': 1}, '81': {'stock': 10000, 'price': 1}, '85': {'stock': 10000, 'price': 1}, '89': {'stock': 10000, 'price': 1}, '93': {'stock': 10000, 'price': 1}, '97': {'stock': 10000, 'price': 1}, '101': {'stock': 9999, 'price': 1}, '105': {'stock': 9999, 'price': 1}, '109': {'stock': 9999, 'price': 1}, '113': {'stock': 10000, 'price': 1}, '117': {'stock': 10000, 'price': 1}, '121': {'stock': 10000, 'price': 1}, '125': {'stock': 9997, 'price': 1}, '129': {'stock': 10000, 'price': 1}, '133': {'stock': 10000, 'price': 1}, '137': {'stock': 9999, 'price': 1}, '141': {'stock': 9999, 'price': 1}, '145': {'stock': 10000, 'price': 1}, '149': {'stock': 10000, 'price': 1}, '153': {'stock': 10000, 'price': 1}, '157': {'stock': 10000, 'price': 1}, '161': {'stock': 10000, 'price': 1}, '165': {'stock': 10000, 'price': 1}, '169': {'stock': 10000, 'price': 1}, '173': {'stock': 9999, 'price': 1}, '177': {'stock': 10000, 'price': 1}, '181': {'stock': 10000, 'price': 1}, '185': {'stock': 10000, 'price': 1}, '189': {'stock': 10000, 'price': 1}, '193': {'stock': 10000, 'price': 1}, '197': {'stock': 9999, 'price': 1}, '201': {'stock': 10000, 'price': 1}, '205': {'stock': 9999, 'price': 1}, '209': {'stock': 10000, 'price': 1}, '213': {'stock': 10000, 'price': 1}, '217': {'stock': 10000, 'price': 1}, '221': {'stock': 9999, 'price': 1}, '225': {'stock': 9999, 'price': 1}, '229': {'stock': 9998, 'price': 1}, '233': {'stock': 10000, 'price': 1}, '237': {'stock': 10000, 'price': 1}, '241': {'stock': 10000, 'price': 1}, '245': {'stock': 10000, 'price': 1}, '249': {'stock': 9998, 'price': 1}, '253': {'stock': 10000, 'price': 1}, '257': {'stock': 10000, 'price': 1}, '261': {'stock': 10000, 'price': 1}, '265': {'stock': 10000, 'price': 1}, '269': {'stock': 9999, 'price': 1}, '273': {'stock': 10000, 'price': 1}, '277': {'stock': 10000, 'price': 1}, '281': {'stock': 10000, 'price': 1}, '285': {'stock': 9999, 'price': 1}, '289': {'stock': 10000, 'price': 1}, '293': {'stock': 10000, 'price': 1}, '297': {'stock': 10000, 'price': 1}, '301': {'stock': 10000, 'price': 1}, '305': {'stock': 10000, 'price': 1}, '309': {'stock': 10000, 'price': 1}, '313': {'stock': 9999, 'price': 1}, '317': {'stock': 10000, 'price': 1}, '321': {'stock': 10000, 'price': 1}, '325': {'stock': 10000, 'price': 1}, '329': {'stock': 10000, 'price': 1}, '333': {'stock': 10000, 'price': 1}, '337': {'stock': 9999, 'price': 1}, '341': {'stock': 10000, 'price': 1}, '345': {'stock': 9999, 'price': 1}, '349': {'stock': 10000, 'price': 1}, '353': {'stock': 10000, 'price': 1}, '357': {'stock': 10000, 'price': 1}, '361': {'stock': 10000, 'price': 1}, '365': {'stock': 10000, 'price': 1}, '369': {'stock': 10000, 'price': 1}, '373': {'stock': 10000, 'price': 1}, '377': {'stock': 10000, 'price': 1}, '381': {'stock': 10000, 'price': 1}, '385': {'stock': 10000, 'price': 1}, '389': {'stock': 9999, 'price': 1}, '393': {'stock': 10000, 'price': 1}, '397': {'stock': 10000, 'price': 1}, '401': {'stock': 10000, 'price': 1}, '405': {'stock': 10000, 'price': 1}, '409': {'stock': 10000, 'price': 1}, '413': {'stock': 10000, 'price': 1}, '417': {'stock': 10000, 'price': 1}, '421': {'stock': 10000, 'price': 1}, '425': {'stock': 9999, 'price': 1}, '429': {'stock': 10000, 'price': 1}, '433': {'stock': 10000, 'price': 1}, '437': {'stock': 10000, 'price': 1}, '441': {'stock': 10000, 'price': 1}, '445': {'stock': 10000, 'price': 1}, '449': {'stock': 10000, 'price': 1}, '453': {'stock': 10000, 'price': 1}, '457': {'stock': 10000, 'price': 1}, '461': {'stock': 9999, 'price': 1}, '465': {'stock': 10000, 'price': 1}, '469': {'stock': 10000, 'price': 1}, '473': {'stock': 9999, 'price': 1}, '477': {'stock': 9998, 'price': 1}, '481': {'stock': 10000, 'price': 1}, '485': {'stock': 10000, 'price': 1}, '489': {'stock': 10000, 'price': 1}, '493': {'stock': 10000, 'price': 1}, '497': {'stock': 9999, 'price': 1}, '501': {'stock': 9999, 'price': 1}, '505': {'stock': 10000, 'price': 1}, '509': {'stock': 10000, 'price': 1}, '513': {'stock': 10000, 'price': 1}, '517': {'stock': 10000, 'price': 1}, '521': {'stock': 10000, 'price': 1}, '525': {'stock': 9999, 'price': 1}, '529': {'stock': 9999, 'price': 1}, '533': {'stock': 10000, 'price': 1}, '537': {'stock': 9999, 'price': 1}, '541': {'stock': 9999, 'price': 1}, '545': {'stock': 10000, 'price': 1}, '549': {'stock': 10000, 'price': 1}, '553': {'stock': 10000, 'price': 1}, '557': {'stock': 10000, 'price': 1}, '561': {'stock': 10000, 'price': 1}, '565': {'stock': 10000, 'price': 1}, '569': {'stock': 10000, 'price': 1}, '573': {'stock': 10000, 'price': 1}, '577': {'stock': 9999, 'price': 1}, '581': {'stock': 9999, 'price': 1}, '585': {'stock': 10000, 'price': 1}, '589': {'stock': 10000, 'price': 1}, '593': {'stock': 10000, 'price': 1}, '597': {'stock': 9999, 'price': 1}, '601': {'stock': 10000, 'price': 1}, '605': {'stock': 10000, 'price': 1}, '609': {'stock': 10000, 'price': 1}, '613': {'stock': 10000, 'price': 1}, '617': {'stock': 10000, 'price': 1}, '621': {'stock': 10000, 'price': 1}, '625': {'stock': 10000, 'price': 1}, '629': {'stock': 10000, 'price': 1}, '633': {'stock': 10000, 'price': 1}, '637': {'stock': 10000, 'price': 1}, '641': {'stock': 10000, 'price': 1}, '645': {'stock': 10000, 'price': 1}, '649': {'stock': 10000, 'price': 1}, '653': {'stock': 10000, 'price': 1}, '657': {'stock': 10000, 'price': 1}, '661': {'stock': 10000, 'price': 1}, '665': {'stock': 10000, 'price': 1}, '669': {'stock': 9999, 'price': 1}, '673': {'stock': 9999, 'price': 1}, '677': {'stock': 10000, 'price': 1}, '681': {'stock': 9999, 'price': 1}, '685': {'stock': 10000, 'price': 1}, '689': {'stock': 10000, 'price': 1}, '693': {'stock': 10000, 'price': 1}, '697': {'stock': 10000, 'price': 1}, '701': {'stock': 10000, 'price': 1}, '705': {'stock': 9999, 'price': 1}, '709': {'stock': 9999, 'price': 1}, '713': {'stock': 10000, 'price': 1}, '717': {'stock': 10000, 'price': 1}, '721': {'stock': 10000, 'price': 1}, '725': {'stock': 10000, 'price': 1}, '729': {'stock': 10000, 'price': 1}, '733': {'stock': 10000, 'price': 1}, '737': {'stock': 10000, 'price': 1}, '741': {'stock': 10000, 'price': 1}, '745': {'stock': 10000, 'price': 1}, '749': {'stock': 10000, 'price': 1}, '753': {'stock': 10000, 'price': 1}, '757': {'stock': 9998, 'price': 1}, '761': {'stock': 10000, 'price': 1}, '765': {'stock': 9999, 'price': 1}, '769': {'stock': 9999, 'price': 1}, '773': {'stock': 10000, 'price': 1}, '777': {'stock': 10000, 'price': 1}, '781': {'stock': 10000, 'price': 1}, '785': {'stock': 10000, 'price': 1}, '789': {'stock': 10000, 'price': 1}, '793': {'stock': 10000, 'price': 1}, '797': {'stock': 10000, 'price': 1}, '801': {'stock': 10000, 'price': 1}, '805': {'stock': 9999, 'price': 1}, '809': {'stock': 10000, 'price': 1}, '813': {'stock': 10000, 'price': 1}, '817': {'stock': 10000, 'price': 1}, '821': {'stock': 10000, 'price': 1}, '825': {'stock': 9999, 'price': 1}, '829': {'stock': 10000, 'price': 1}, '833': {'stock': 10000, 'price': 1}, '837': {'stock': 10000, 'price': 1}, '841': {'stock': 10000, 'price': 1}, '845': {'stock': 10000, 'price': 1}, '849': {'stock': 10000, 'price': 1}, '853': {'stock': 10000, 'price': 1}, '857': {'stock': 10000, 'price': 1}, '861': {'stock': 9999, 'price': 1}, '865': {'stock': 9999, 'price': 1}, '869': {'stock': 10000, 'price': 1}, '873': {'stock': 10000, 'price': 1}, '877': {'stock': 9998, 'price': 1}, '881': {'stock': 9999, 'price': 1}, '885': {'stock': 10000, 'price': 1}, '889': {'stock': 10000, 'price': 1}, '893': {'stock': 10000, 'price': 1}, '897': {'stock': 10000, 'price': 1}, '901': {'stock': 10000, 'price': 1}, '905': {'stock': 10000, 'price': 1}, '909': {'stock': 10000, 'price': 1}, '913': {'stock': 10000, 'price': 1}, '917': {'stock': 10000, 'price': 1}, '921': {'stock': 10000, 'price': 1}, '925': {'stock': 10000, 'price': 1}, '929': {'stock': 9999, 'price': 1}, '933': {'stock': 9999, 'price': 1}, '937': {'stock': 9999, 'price': 1}, '941': {'stock': 10000, 'price': 1}, '945': {'stock': 10000, 'price': 1}, '949': {'stock': 10000, 'price': 1}, '953': {'stock': 9999, 'price': 1}, '957': {'stock': 10000, 'price': 1}, '961': {'stock': 9999, 'price': 1}, '965': {'stock': 10000, 'price': 1}, '969': {'stock': 10000, 'price': 1}, '973': {'stock': 10000, 'price': 1}, '977': {'stock': 10000, 'price': 1}, '981': {'stock': 10000, 'price': 1}, '985': {'stock': 10000, 'price': 1}, '989': {'stock': 9999, 'price': 1}, '993': {'stock': 10000, 'price': 1}, '997': {'stock': 10000, 'price': 1}}
#         }
#
#         response = await self.service.get_query_state_response(query)
#         print(response)
#         self.assertEqual(response, expected_response)
#
#     async def test_get_query_state_response_get_key_state(self):
#         query = {'type': 'GET_KEY_STATE', 'uuid': '12345', 'operator': 'operator1', 'key': 1}
#
#         with patch.object(self.service, 'get_partition', return_value=0):
#             expected_response = {
#                 'uuid': '12345',
#                 'epoch': 42,
#                 'operator_key_state': 'value1'
#             }
#
#             response = await self.service.get_query_state_response(query)
#             self.assertEqual(response, expected_response)
#
