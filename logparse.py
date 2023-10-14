#!/usr/bin/env python

import fileinput
import re
import sys
from prettytable import PrettyTable

class CharmLog:

        #Regex that anchors itself to a timestamp as a lookbehind to make sure 
        #it captures the correct severity level
        message_severity_regex = r'(?<=[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\s)((INFO)|(DEBUG)|(WARNING)|(ERROR))'

        #These are static counts for keeping track of totals across all instances of units/charms
        grand_total = {'INFO': 0, 'DEBUG': 0, 'WARNING': 0, 'ERROR': 0, 'Total': 0}
        grand_total_duplicates= {'INFO': 0, 'DEBUG': 0, 'WARNING': 0, 'ERROR': 0, 'Total': 0}

        def __init__(self):
                #This will store the messages for each unit/charm
                self.log_messages={'INFO': set(), 'DEBUG': set(), 'WARNING': set(), 'ERROR': set()}\
                #This will keep track of duplicates
                self.amount_of_duplicates={'INFO': 0, 'DEBUG': 0, 'WARNING': 0, 'ERROR': 0}
        
        def determine_message_severity_type(log_message):
                return re.search(CharmLog.message_severity_regex, log_message).group(0)
                

        def add_log_message(self, log_message):
                try:
                        severity_type = CharmLog.determine_message_severity_type(log_message)
                        if log_message in self.log_messages[severity_type]:             #if message was already saved
                                self.amount_of_duplicates[severity_type]+=1             #we increment amount of duplicate for specific message
                                CharmLog.grand_total_duplicates[severity_type]+=1       #and increment static total
                                CharmLog.grand_total_duplicates["Total"]+=1
                        else:
                                self.log_messages[severity_type].add(log_message)       #otherwise just add message to set

                        CharmLog.grand_total[severity_type]+=1    
                        CharmLog.grand_total["Total"]+=1
                except:
                        print("Count not parse line: " + log_message)
                

        def get_amount_messages(self, severity_type):
                #Returns amount of messages for given severity plus number of duplicates to give total amount
                return len(self.log_messages[severity_type])+self.amount_of_duplicates[severity_type]

        def get_total_amount_messages(self):
                #Returns total amount of messages across all severities for given Unit/Charm
                total = 0
                for logs in self.log_messages.values():
                        total += len(logs)
                return total+self.get_total_amount_duplicates() #add nr of duplicates to give total amount
        
        def get_total_amount_duplicates(self):
                total = 0
                for duplicates in self.amount_of_duplicates.values():
                        total += duplicates
                return total

        def has_warnings(self):
                return len(self.log_messages['WARNING']) > 0


#This is a just a text formatting class for output
class OutputGenerator:
        
        def generate_output_table(units):
                output_table = PrettyTable()
                output_table.field_names = ['Charm/Unit Name', 'Info', 'Debug', 'Warning', 'Error', 'Total']
                for unit_name in sorted(units.keys()):
                        output_table.add_row([
                                unit_name, 
                                units[unit_name].get_amount_messages('INFO'),
                                units[unit_name].get_amount_messages('DEBUG'),
                                units[unit_name].get_amount_messages('WARNING'),
                                units[unit_name].get_amount_messages('ERROR'),
                                units[unit_name].get_total_amount_messages(),
                                ])
                return output_table

        def generate_duplicates_output_table(units):
                output_table = PrettyTable()
                output_table.field_names = ['Info', 'Debug', 'Warning', 'Error', 'Total']
                output_table.add_row([
                                CharmLog.grand_total_duplicates['INFO'],
                                CharmLog.grand_total_duplicates['DEBUG'],
                                CharmLog.grand_total_duplicates['WARNING'],
                                CharmLog.grand_total_duplicates['ERROR'],
                                CharmLog.grand_total_duplicates['Total']
                                ])
                return output_table

        def generate_total_output_table(units):
                output_table = PrettyTable()
                output_table.field_names = ['Info', 'Debug', 'Warning', 'Error', 'Total']
                output_table.add_row([
                                CharmLog.grand_total['INFO'],
                                CharmLog.grand_total['DEBUG'],
                                CharmLog.grand_total['WARNING'],
                                CharmLog.grand_total['ERROR'],
                                CharmLog.grand_total['Total']
                                ])
                return output_table

        def output(units):
                units_with_warnings = {k: v for k, v in units.items() if v.has_warnings()}
                units_without_warnings = {k: v for k, v in units.items() if not v.has_warnings()}
                if len(units_with_warnings) != 0:
                        print('Charms that produced Warnings:')
                        print(OutputGenerator.generate_output_table(units_with_warnings))
                else:
                        print('No charms produced Warnings')

                if len(units_without_warnings) != 0:
                        print('Rest of charms:')
                        print(OutputGenerator.generate_output_table(units_without_warnings))
                else:
                        print('There were no charms without Warnings')

                print('Amount of duplicates:')
                print(OutputGenerator.generate_duplicates_output_table(units))
                print('Totals:')
                print(OutputGenerator.generate_total_output_table(units))
                
class LineParser:
        generic_unit_name_regex = r'^[a-zA-Z0-9-]*?-[0-9]*?:'           #Prefix regex so that we don't match lines without a unit name
        time_stamp_regex = r'[0-9][0-9]:[0-9][0-9]:[0-9][0-9]'          #Match timestamp
        message_severity_regex = r'((WARNING)|(DEBUG)|(INFO)|(ERROR))'  #Match severity

        #Combine all of the above regex's to make sure we match a parse-able log line
        # i.e. something that looks like 'unit-sql-0: 00:21:00 WARNING'
        log_line_regex = generic_unit_name_regex + '\s' + time_stamp_regex + '\s' + message_severity_regex


        #Function that figures out the unit/charm name from a log line
        def parse_unit_name(log_line):
                unit_name_regex = r'(?<=unit-)[a-z0-9-]*(?=-[0-9]*:)'
                unit_name = re.search(unit_name_regex, log_line)
                if unit_name is not None:
                        return unit_name.group(0)
                else:
                        #In case we have a unit like "machine-0" or "controller-0" that can't be matched
                        #we just group the message into generic juju messages
                        return 'juju-generic'

        #Function that checks the line is parseable and then returns the unit/charm name
        def parse_line(log_line):
                if re.match(LineParser.log_line_regex, log_line):
                        unit_name = LineParser.parse_unit_name(log_line)
                        return unit_name
                else:
                        return None

def main():
        unit_to_filter = None
        if len(sys.argv) < 2:
                print('Wrong usage\nExample: python logparse.py <filename> <charm-name>\n<charm-name> is optional')
                exit(1)
        elif len(sys.argv) >= 3:
                unit_to_filter = sys.argv[2]
        file_to_parse = sys.argv[1]

        units = {}  #Dict where key is the name of unit/charm and value is an instance of CharmLog

        try:
                for line in fileinput.input([file_to_parse]):
                        unit_name=LineParser.parse_line(line)                                   #Determine unit/charm name
                        if unit_name is not None:                                               #check if parsed correctly
                                if (unit_to_filter == None) or (unit_to_filter == unit_name):   #check whether we have a filter set
                                        if unit_name not in units:                              #check if unit/charm already exists in dict
                                                units[unit_name] = CharmLog()                   #if not instantiate new CharmLog()
                                        units[unit_name].add_log_message(line.strip())          #add unit/charm to the CharmLog() instance
        except FileNotFoundError:
                print('File ' + file_to_parse + ' not found.')
                exit(1)
        OutputGenerator.output(units)
        exit(0)

if __name__ == '__main__':
    main()