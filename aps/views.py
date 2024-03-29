#Pemanggilan Libary
from aps.forms import UserForm,UserProfileInfoForm
from cryptography.fernet import Fernet
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from .models import mainkey,Profile,PairKeyReq
import base64
import datetime
import hvac
import mysql.connector
import pyautogui
import pybase64
import sys
import time

# Database Connection
db = mysql.connector.connect(host='localhost',database='pki',user='root',password='')
key = Fernet.generate_key()
f = Fernet(key)

client = hvac.Client(url='http://127.0.0.1:8200')

auth = Profile.objects.all()
job = {'auth': auth}

def index(request):
    return render(request,'aps/index.html')

@login_required
def create_key(request):

    test = mainkey.objects.all()[:1]
    context = {'test': test}

    return render(request, 'aps/newkey.html', context )   
    
@login_required
def create_key_submit(request):
    if request.method == 'POST':
        
        #sql_select_Query = "select kunci from mainkey where id = '{{comparison}}' "
        #cursor = db.cursor()
        #cursor.execute(sql_select_Query)
        
        #print(cursor.fetchall()) 
        
        #coba = f.decrypt(b) 
        #pyautogui.alert(coba)

        encrypttype = request.POST.get('encrypttype')
        bit         = request.POST.get('bit')    

        if encrypttype == 'RSA':

            if bit  =='512':
                bit = 512
            elif bit  =='1024':
                bit = 1024
            else :
                bit = 2048           
            
            encrypttype = encrypttype

            private_key_rsa = rsa.generate_private_key(
                public_exponent=65537,
                key_size= bit ,
                backend=default_backend()
            )

            kuncipub1 = private_key_rsa.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(b'{{ encrypttype }}')
                )

            public_key = private_key_rsa.public_key()
            kuncipub = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
                   
        elif encrypttype =='ECDSA':

            encrypttype = encrypttype

            private_key_ecdsa = ec.generate_private_key(
                ec.SECP384R1(), default_backend()
            )

            data = b"{{ encrypttype }}"
            
            signature = private_key_ecdsa.sign(
                data,
                ec.ECDSA(hashes.SHA256())
            ) 

            public_key = private_key_ecdsa.public_key()
            hasil = public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))

            kuncipub = hasil
            kuncipub1 = signature

        elif encrypttype =='DSA':

            if bit  =='1024':
                bit = 1024
            elif bit  =='2048':
                bit = 2048
            else :
                bit = 3072   

            encrypttype = encrypttype
            
            private_key_dsa = dsa.generate_private_key(
                key_size=bit,
                backend=default_backend()
            )

            data = b"{{ encrypttype }}"
            
            signature = private_key_dsa.sign(
                data,
                hashes.SHA256()
            )

            public_key = private_key_dsa.public_key()

            hasil = public_key.verify(
                signature,
                data,
                hashes.SHA256()
            )

            kuncipub = hasil
            kuncipub1 = signature

        elif encrypttype =='HASH':

            encrypttype = encrypttype

            if bit == 'SHA224': 
                key = hashes.SHA224()
            elif  bit == 'SHA256': 
                key = hashes.SHA256()  
            elif  bit == 'SHA384': 
                key = hashes.SHA384()
            else :
                key = hashes.SHA512()                

            digest = hashes.Hash(key, backend=default_backend())
            digest.update(b"{{ encrypttype }}")
            hasil = digest.finalize()

            kuncipub = 'none'
            kuncipub1 = hasil
        
        else :
            kuncipub = 'Failed'
            kuncipub1 = 'Failed'            
            
        context= {
            'public': kuncipub,
            'private':kuncipub1,
        }

        
        return render(request, 'aps/newkey.html',context)

    else :   
        pyautogui.alert('Failed')
        return render(request, 'aps/newkey.html')
      
@login_required
def key_submit(request):
    if request.method == 'POST':
        pyautogui.alert('Save Sucesfully')
        return render(request, 'aps/newkey.html')
    else :   
        pyautogui.alert('Failed')
        return render(request, 'aps/newkey.html')      

@login_required
def master_key(request):

    test = mainkey.objects.all()[:1]
    context = {'test': test}
    return render(request, 'aps/masterkey.html' , context ) 

@login_required
def master_key_submit(request):
        if request.method == 'POST':

            def base64ify(bytes_or_str):
                if sys.version_info[0] >= 3 and isinstance(bytes_or_str, str):
                    input_bytes = bytes_or_str.encode('utf8')
                else:
                    input_bytes = bytes_or_str

                output_bytes = base64.urlsafe_b64encode(input_bytes)
    
                if sys.version_info[0] >= 3:
                    return output_bytes.decode('ascii')
                else:
                    return output_bytes
            
            
            cursor = db.cursor(buffered=True)

            nik = request.POST.get('id')
            keyname = request.POST.get('keyname')


            client.secrets.transit.create_key(name=keyname)

            client.secrets.transit.update_key_configuration(
                name=keyname,                
                deletion_allowed=True,
                exportable=True,
            )

            export_key_response = client.secrets.transit.export_key(
                name=keyname,
                key_type='hmac-key',
            )

            ts = time.time()
            timestamp = (datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))
            key = export_key_response['data']['keys']
        
            sql1 = "insert into mainkey(no, id, key_name, time_start) VALUES(%s, %s, %s, %s)"
            val = ("",nik,keyname,timestamp)

            cursor.execute(sql1,val)
            db.commit()

            pyautogui.alert('Master Key Created')
            return render(request, 'aps/index.html')  

        else :
            pyautogui.alert('Failed')  
            return render(request, 'aps/masterkey.html') 

@login_required
def special(request):
    return HttpResponse("You are logged in !")

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))

def about(request):
    return render(request, 'aps/about.html')   

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request,user)

                return render(request, 'aps/index.html')

            else:
                return HttpResponse("Your account was inactive.")
        else:
            print("Someone tried to login and failed.")
            print("They used username: {} and password: {}".format(username,password))
            pyautogui.alert('Please check again your Username or Password')
            return render(request, 'aps/login.html', {})
    else:
        return render(request, 'aps/login.html', {})

@login_required
def list_key(request):

    test = mainkey.objects.all()
    context = {'test': test}

    return render(request, 'aps/list_key.html', context)  

@login_required
def rotate_key_master(request) :
    if request.method == 'POST':
        keyname = request.POST.get('keyname')
        client.secrets.transit.rotate_key(name=keyname)
        pyautogui.alert('Rotete Key Sucess') 
        return render(request, 'aps/index.html') 
    else :
        pyautogui.alert('Rotete Key Failed')  
        return render(request, 'aps/list_key.html') 

@login_required
def delete_key_master(request) :
    if request.method == 'POST':
        keyname = request.POST.get('keydelete')

        cursor = db.cursor(buffered=True)
        
        sql1 = """Delete from mainkey where key_name = %s"""
        val = keyname
        cursor.execute(sql1,(val,))
        db.commit()

        client.secrets.transit.delete_key(name=keyname)
        pyautogui.alert('Delete Key Sucess') 
        return render(request, 'aps/index.html') 
    else :
        pyautogui.alert('Delete Keys Key Failed')  
        return render(request, 'aps/list_key.html') 

@login_required
def requestcsca(request):

    test = mainkey.objects.all()[:1]
    context = {'test': test}
    return render(request, 'aps/requestcsca.html', context) 

@login_required
def validkey(request):

    return render(request, 'aps/validkey.html')    

@login_required
def validkeysubmit(request):
    if request.method == 'POST':
        
        issuing_certificates = request.POST.get('issuing_certificates')
        crlurl = request.POST.get('crlurl')        

        client.sys.enable_secrets_engine(
            backend_type='transit',
            path='transit',

        )

        client.sys.enable_secrets_engine(
            backend_type='pki',
            path='pki',
        )
        set_crl_configuration_response = client.secrets.pki.set_crl_configuration(
            expiry='1095h',
            disable=False
        )        

        set_urls_response = client.secrets.pki.set_urls(
            {
            'issuing_certificates': [issuing_certificates],
            'crl_distribution_points': [crlurl]
            }
        )

        pyautogui.alert('Configure Sucessfull') 
        return render(request, 'aps/index.html') 

    else :
        pyautogui.alert('failed') 
        return render(request, 'aps/index.html') 

@login_required
def requestkey(request):
        if request.method == 'POST':
            jenis           = 'exported'
            bits            = '2048'
            masterkey       = request.POST.get('masterkey')
            organization    = request.POST.get('organization')
            country         = request.POST.get('country')
            kota            = request.POST.get('kota')
            provinsi        = request.POST.get('province')
            jalan           = request.POST.get('address')
            pos             = request.POST.get('kodepos')
            status          = '0'
            privkey         = ''
            pubkey          = ''

            cursor = db.cursor(buffered=True)

            sql1 = "insert into aps_pairkeyreq(no, masterkey, negara, kota, provinsi, jalan, pos, status, bit,organization,jenis,privkey,pubkey) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            val = ("",masterkey,country,kota,provinsi,jalan,pos,status,bits,organization,jenis,privkey,pubkey)

            cursor.execute(sql1,val)
            db.commit()


            pyautogui.alert('Register succes') 
            return render(request, 'aps/index.html')   
        else :  
            pyautogui.alert('failed') 
            return render(request, 'aps/index.html')   

@login_required
def caapprov(request):
 
    pairkey = PairKeyReq.objects.all()
    createkey = {'pairkey': pairkey} 

    return render(request, 'aps/caapprov.html', createkey) 

@login_required
def keypairca(request):
    if request.method == 'POST':

        masterkey       = request.POST.get('masterkey')
        organization    = request.POST.get('organisasi')
        country         = request.POST.get('negara')
        kota            = request.POST.get('provinsi')
        provinsi        = request.POST.get('kota')
        jalan           = request.POST.get('jalan')
        pos             = request.POST.get('pos')
        status          = request.POST.get('approval')

        generate_root_response = client.secrets.pki.generate_root(
            type='exported',
            common_name=masterkey,
            extra_params=
            {
                "ttl" : "365h",
                "key_type": "rsa",
                "key_bits": "2048",
                "organization": organization,
                "country":country,
                "locality/city":kota,
                "province/state":provinsi,
                "street_address": jalan,
                "postal_code":pos  
            } 
        )
        
        cursor = db.cursor(buffered=True)
        sql1 = """ UPDATE aps_pairkeyreq SET status = %s where masterkey = %s """            
        val = (status,masterkey)

        cursor.execute(sql1,val)
        db.commit()

        pyautogui.alert('Generated Key Successfull') 
        return render(request, 'aps/index.html')    

    else:    
        
        pyautogui.alert('failed') 
        return render(request, 'aps/index.html')    

@login_required
def listkeyca(request):

    pairkey = PairKeyReq.objects.all()
    createkey = {'pairkey': pairkey} 

    return render(request, 'aps/listkeyca.html',createkey)         

@login_required
def certifcate(request):

    #if request.method == 'POST':

        #generate_intermediate_response = client.secrets.pki.generate_intermediate(
            #type='exported',
            #common_name='Vault integration tests'
        #)

    pyautogui.alert('ok')
    return render(request, 'aps/certificate.html')    

@login_required
def certifcateINT(request):


    if request.method == 'POST':

        #generate_intermediate_response = client.secrets.pki.generate_intermediate(
            #type='exported',
            #common_name='Vault integration tests'
        #)

        pyautogui.alert('create ok')
        return render(request, 'aps/certificate.html') 



