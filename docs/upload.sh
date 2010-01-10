cd _build
rm html.zip
cd html
zip -r ../html.zip *
cd ../..
echo -n "username:password="
read credentials
curl -X POST http://pypi.python.org/pypi \
     -F :action=doc_upload -F name=django-jython -F content=@_build/html.zip  \
     --user $credentials
