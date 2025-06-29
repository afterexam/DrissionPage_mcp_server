


from DrissionPage import ChromiumPage
 
cp = ChromiumPage()
cp.get('https://1997.pro/themes/theme-yazong/assets/html/eazy_check.html')
button = cp.ele('xpath://button')

cp.actions.move_to(button).click()
# input("11")