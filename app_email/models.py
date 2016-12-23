from __future__ import unicode_literals

from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User, Group
from sorl.thumbnail import get_thumbnail
from django.template.defaultfilters import slugify
import datetime
from django.template import loader
from django.utils import timezone
from datetime import timedelta
from django.db.models import Prefetch
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_init, pre_init, post_save
import math
from django.core.urlresolvers import reverse
from django.conf import settings
from decimal import Decimal
from emailer.settings import *
from urlparse import urlparse
from django.core.files import File
from amazon.api import AmazonAPI
import bottlenose.api
import urllib
import requests, json
from .tasks import email_task


class Image(models.Model):
    img_path = 'product/'
    caption = models.CharField(max_length=255,null=True,blank=True)
    img = models.ImageField(upload_to=img_path)
    slug=models.SlugField(max_length=255)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.id is None:
            super(Image, self).save(*args, **kwargs)
        if self.caption is None or self.caption == '':
            self.caption = self.id 
        super(Image, self).save(*args, **kwargs)
        if self.slug is None or self.slug == '':
            self.slug = slugify(self.caption)
        super(Image, self).save(*args, **kwargs)

class Website(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=200,null=True,blank=True)

    def __unicode__(self):
        return self.name

class Basic(models.Model):
    name = models.CharField(max_length=255,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    slug=models.SlugField(max_length=255,null=True,blank=True)
    active=models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if (self.name is not None or self.name != '') and (self.slug is None or self.slug == ''):
            self.slug = slugify(self.name)
        super(Basic, self).save(*args, **kwargs)

    def get_basic_json(self):
        var={}
        var['name']=self.name
        var['description'] =self.description
        var['slug']=self.slug
        var['created_on']=self.created_on
        return var

    class Meta:
        abstract = True

class Product(Basic):
    website = models.ForeignKey(Website,null=True,blank=True)
    url = models.TextField(null=True,blank=True)
    author_description = models.TextField(null=True,blank=True)
    aff_url = models.TextField(null=True,blank=True)
    sku = models.CharField(max_length=10,null=True,blank=True,verbose_name='Product code')
    pid = models.CharField(max_length=30,null=True,blank=True,verbose_name='Website Product code')
    mrp = models.FloatField(null=True,blank=True)
    price = models.FloatField(null=True,blank=True)
    def add_info(self):

        if self.website.name == "Flipkart":
            o = urlparse(self.url)
            pid = o.query.split('&')[0][1:]
            new_url = 'https://affiliate-api.flipkart.net/affiliate/product/json?'+pid
            header = {
            'Fk-Affiliate-Token':Fk_Affiliate_Token,
            'Fk-Affiliate-Id':Fk_Affiliate_Id,
            }
            r = requests.get(new_url, headers=header)
            data = json.loads(r._content)
            self.pid = data['productBaseInfo']['productIdentifier']['productId']
            self.mrp = data['productBaseInfo']['productAttributes']['maximumRetailPrice']['amount']
            self.description = data['productBaseInfo']['productAttributes']['productDescription']
            self.price = data['productBaseInfo']['productAttributes']['sellingPrice']['amount']
            self.aff_url = data['productBaseInfo']['productAttributes']['productUrl']
            self.name = data['productBaseInfo']['productAttributes']['title']
            try:
                try:
                    img_url = data['productBaseInfo']['productAttributes']['imageUrls']['unknown']
                except:
                    img_url = data['productBaseInfo']['productAttributes']['imageUrls']['800x800']
            except:
                try:
                    img_url = data['productBaseInfo']['productAttributes']['imageUrls']['400x400']
                except:
                    img_url = data['productBaseInfo']['productAttributes']['imageUrls']['200x200']

            name = urlparse(img_url).path.split('/')[-1]
            content = urllib.urlretrieve(img_url)
            pi = ProductImage()
            pi.product = self
            pi.img.save(name, File(open(content[0])), save=True)
            pi.save()
            self.save()
        elif self.website.name == "Amazon":
            o = urlparse(self.url)
            pid = o.path.split('/')[3]
            amazon = AmazonAPI(AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_ASSOC_TAG, region="IN")
            product = amazon.lookup(ItemId=pid)
            self.pid = pid
            if product.list_price[0] is None:
                self.mrp = product.price_and_currency[0]
            else:
                self.mrp = product.list_price[0]
            self.price = product.price_and_currency[0]
            self.name = product.title
            self.aff_url = product.offer_url
            self.description =product.features
            try:
                name = urlparse(product.large_image_url).path.split('/')[-1]
                pi = ProductImage()
                content = urllib.urlretrieve(product.large_image_url)
                pi.product = self
                pi.img.save(name, File(open(content[0])), save=True)
                pi.save()
            except:
                pass
            for ig in product.images:
                img_url = str(ig.LargeImage.URL)
                if img_url != product.large_image_url:
                    name = urlparse(img_url).path.split('/')[-1]
                    content = urllib.urlretrieve(img_url)
                    pi = ProductImage()
                    pi.product = self
                    pi.img.save(name, File(open(content[0])), save=True)
                    pi.save()
            
            self.save()

        elif self.website.name == "Snapdeal":
            o = urlparse(self.url)
            pid = o.path.split('/')[3]
            new_url = 'http://affiliate-feeds.snapdeal.com/feed/product?id='+pid
            header = {
            'Snapdeal-Token-Id':Snapdeal_Token_Id,
            'Snapdeal-Affiliate-Id':Snapdeal_Affiliate_Id,
            'Accept': 'application/json',
            }
            r = requests.get(new_url, headers=header)
            data = json.loads(r._content)
            self.pid = data['id']
            self.mrp = data['mrp']
            self.description = data['description']
            self.price = data['effectivePrice']
            self.aff_url = data['link']
            self.name = data['title']
            img_url = data['imageLink']
            content = urllib.urlretrieve(img_url)
            name = urlparse(img_url).path.split('/')[-1]
            pi = ProductImage()
            pi.product = self
            pi.img.save(name, File(open(content[0])), save=True)
            pi.save()
            self.save()

        return None

    def save(self, *args, **kwargs):
        super(Product, self).save(*args, **kwargs)
        if not self.sku:
            self.sku = 'PRO'+str(10000+self.id)
            self.active = True
        if not self.name or self.name == '':
            self.add_info()
        super(Product, self).save(*args, **kwargs)

class ProductImage(Image):
    product = models.ForeignKey(Product,related_name='image')

class EmailInfo(models.Model):
    products = models.ManyToManyField(Product,related_name="email_info", blank = True)
    to_group = models.ManyToManyField(Group, related_name="email_info")
    subject=models.CharField(max_length=255)
    # select_template=
    send=models.BooleanField(default=False)
    def save(self, *args, **kwargs):
        #self.slug = slugify(self.name)
        if self.send == True:
            context = {

                'products' : self.products.all(),                    
                    }
            template_name = "email/email.html"
            message = loader.render_to_string(template_name, context)
            groups = self.to_group.all()
            email = []
            for group in groups:
                group_users=group.user_set.all()
                for j in group_users:
                    email.append(j.email)

            email_task.delay(
                subject=self.subject,
                sender='info@dealscount.in',
                receiver= email,
                html_message=message
            )
        super(EmailInfo, self).save(*args, **kwargs)
        
    def __unicode__(self):
        return self.subject or u''