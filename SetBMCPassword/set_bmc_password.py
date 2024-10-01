import subprocess
import re
import argparse
import sys
import os
from os import path


def checkPreReq(input_file, password_file):
    exit = False
    input_file_exists = path.exists(input_file)
    password_file_exists = path.exists(password_file)
    if not input_file_exists:
        print("Input File does not exists")
        exit = True
    if not password_file_exists:
        print("Password file does not exist")
        exit = True
    try:
        tool_dir = os.environ["SUM_DIR"]
    except KeyError:
        msg = " **** ERROR **** Environment variable SUM_DIR is not set"
        print(msg)
        exit = True
    if exit == True:
        sys.exit()

def get_IP_address(start_ip,end_ip):
    ip_list = []
    start_ip_list = start_ip.split('.')
    end_ip_list = end_ip.split('.')
    start_host = start_ip_list[-1]
    end_host = end_ip_list[-1]
    ip_address_format = re.compile('(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])')

    #Check IP end number and ip address format is correct
    if int(end_host) < int(start_host):
        sys.exit("**** ERROR **** end ip is smaller than start ip")
    if (not (re.match(ip_address_format, start_ip))):
        sys.exit("**** ERROR **** start ip is not correct ip address format")
    if (not (re.match(ip_address_format, end_ip))):
        sys.exit("**** ERROR **** end ip is not correct ip address format")


    #Check the subrange
    for ping in range(int(start_host),(int(end_host))+1):
        address = start_ip_list[0] + '.' + start_ip_list[1] + '.' + start_ip_list[2] +'.' + str(ping)
        res = subprocess.call(['ping','-c','3', address])
        if res == 0:
            print(f'ping to {address} OK')
            ip_list.append(address)
        elif res == 2:
            print(f'no response from, {address}')
        else:
            print(f'ping to, {address}, failed!')
    return ip_list

#parse the input file
#return dictionary containing only the IPMI and passwords
def parse_input_file(file):
    ipmi_to_pass = dict()
    error = []
    try:
        with open(file,'r') as f:
            for each_entry in f:
                list = each_entry.split(',')
                if len(list) != 4:
                    error.append(each_entry)
                else:
                    # From input file, dictionary ipmi to default passwordtry cat
                    ipmi_to_pass[list[2].lower().replace(':', '')] = list[3]

    except FileNotFoundError:
        print("File not Found")
        sys.exit()
    except:
        print("An error has occured")
        sys.exit()
    if len(error) != 0:
        print("ERROR WITH INPUT FILE FORMAT")
        for each_error in error:
            print(each_error)
    else:
        return ipmi_to_pass

#get the arguments
def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file',
                        help = 'File containing list of ip addresses, each entry must be in format Item Number, Serial Number, IPMI Mac, Unique password in this order separated by commas',
                        type = str,
                        nargs = '?',)
    parser.add_argument('password_file',
                        help='File containing password to be changed to',
                        type=str,
                        nargs='?',)
    parser.add_argument('start_IP',
                        help = 'Start of IP range',
                        type = str,
                        nargs = '?')
    parser.add_argument('end_IP',
                        help = 'End of IP Range',
                        type = str,
                        nargs = '?')
    arguments = parser.parse_args()
    input_file = arguments.input_file
    password_file = arguments.password_file
    start_ip = arguments.start_IP
    end_ip = arguments.end_IP
    return input_file, password_file, start_ip, end_ip

#converts the IP addresses to IPMI using arp table
def IP_to_IPMI(ip_address):
    ip_to_ipmi = dict()
    list_of_mac = []
    not_found = []
    mac_address_format = re.compile('[a-fA-F0-9:-]{17}|[a-fA-F0-9]{12}')
    for each_address in ip_address:
        subprocess.call(['ping','-c', '1', each_address], stdout=subprocess.PIPE)
        process = subprocess.Popen(['arp', '-a', each_address], stdout=subprocess.PIPE)
        out, err = process.communicate()
        out = out.decode("utf-8")
        if ('no match found' in  out.lower() or 'No ARP Entries Found' in out or 'incomplete' in out):
            not_found.append(f'{each_address}\t not found.')
        else:
            list_of_mac.append(f'{each_address}\t {re.findall(mac_address_format, out)[0]}')
            ip_to_ipmi[each_address] = ((re.findall(mac_address_format, out)[0]).replace(':','').lower())
    print("LIST OF ALL IP ADDRESSES FOUND")
    for each_mac in list_of_mac:
        print(each_mac)
    print('\n')
    return ip_to_ipmi

#from the IPMI mac from the IP's, match up with the IPMI foud in the input file
def IPMI_to_password(ipmi_list,file):
    final_ipmi_to_pass = dict()
    input_file_dict = parse_input_file(file)
    for ipmi in ipmi_list:
        if(ipmi.lower().replace(':','') in input_file_dict.keys()):
            final_ipmi_to_pass[ipmi] = input_file_dict[ipmi]
    return final_ipmi_to_pass

#map the ip's from original network to the end passwords
def ip_to_ipmi_to_password(ip_to_ipmi,ipmi_to_password):
    ip_to_password = dict()
    for ip in ip_to_ipmi.keys():
        ipmi = ip_to_ipmi[ip].lower().replace(':','')
        if ipmi in ipmi_to_password.keys():
            ip_to_password[ip] = ipmi_to_password[ipmi]
    return ip_to_password

#create the ip list file used by SUM
def make_ip_list_file(ip_to_password):
    try:
        with open("ip.txt", 'w') as f:
            for each_ip in ip_to_password:
                f.write(f'{each_ip}\n')
    except IOError:
        print('Pemission not granted to create files')
        sys.exit()

#get single password from the password file
def check_password_file(password_file):
    password_file_exists = True
    try:
        with open(password_file, 'r') as f:
            password = f.read()
            if password == "":
                print("**** ERROR **** password file is empty")
                password_file_exists = False
    except FileNotFoundError:
        print("Password file not found")
        password_file_exists = False
    except:
        print("An error has occured")
        password_file_exists = False
    return password_file_exists

#with SUM, change all IP in the ip file create to the password file, using the unique passwords
def change_password(ip_to_password, password_file):
    try:
        tool_dir = os.environ["SUM_DIR"]
    except KeyError:
        msg = " **** ERROR **** Environment variable SUM_DIR is not set"
        print(msg)
        sys.exit()
    tool_cmd = f'{tool_dir}/sum'
    try:
        with open("ip.txt",'r') as f:
            with open(password_file,'r') as new_password:
                for each_entry in f:
                    ip = each_entry
                    print(f'{ip}')
                    password = ip_to_password[ip.strip()].strip()
                    ip = ip.strip()
                    subprocess.call([tool_cmd, '-i', ip, '-u', 'ADMIN','-p', password, '-c',
                                     'SetBmcPassword', '--pw_file', password_file])
                    print('\n')
    except:
        print("Error has occured")
        sys.exit()

def main():
    input_file,password_file,start_ip,end_ip = get_arguments()
    checkPreReq(input_file, password_file)
    list_of_ip_addresses = get_IP_address(start_ip,end_ip)
    ip_to_ipmi = IP_to_IPMI(list_of_ip_addresses) #Only contains valid IP addresses to IPMI
    final_ipmi_to_password = IPMI_to_password((ip_to_ipmi.values()),input_file)
    ip_to_password = ip_to_ipmi_to_password(ip_to_ipmi,final_ipmi_to_password)
    make_ip_list_file(ip_to_password)
    password = check_password_file(password_file)
    change_password(ip_to_password,password_file)

    print("FINISHED")

if __name__ == '__main__':
    main()
