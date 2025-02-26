from os import chdir
from os.path import abspath
from pickle import dump
from playwright.sync_api import sync_playwright  # pip install playwright (I use 1.50.0)
from setproctitle import setproctitle  # pip install setproctitle (I use 1.3.4)

def main():
	print('Initializing...')
	initialize()
	print('Downloading...')
	for type, type_data in data.items():
		print(f'  {type}')
		for service, service_data in type_data['services'].items():
			print(f'    {service}')
			page.goto('https://teleco.serviciosmin.gob.es/RPC_Consulta/FrmConsulta.aspx')
			page.click(f'#{type_data["id"]}')
			page.wait_for_load_state('networkidle')
			page.query_selector('#MainContent_cmbServicio').select_option(service_data['id'])
			page.wait_for_load_state('networkidle')
			if service in ('Redes móviles', 'Radiodifusión en FM', 'Radiodifusión en OM'):
				page.fill('#MainContent_txtFrecuenciaDesde', '0')
				page.wait_for_timeout(50)
				page.fill('#MainContent_txtFrecuenciaHasta', '999999999999')
				page.wait_for_timeout(50)
				download(page, service_data)
			elif service == 'Servicio Fijo sin Reserva de Bandas':
				page.fill('#MainContent_txtFrecuenciaDesde', '0')
				page.wait_for_timeout(50)
				page.fill('#MainContent_txtFrecuenciaHasta', '1500000')
				page.wait_for_timeout(50)
				download(page, service_data)
				page.fill('#MainContent_txtFrecuenciaDesde', '1500000')
				page.wait_for_timeout(50)
				page.fill('#MainContent_txtFrecuenciaHasta', '999999999999')
				page.wait_for_timeout(50)
				download(page, service_data)
			elif service in ('Radio digital', 'Televisión digital'):
				for community in communities:
					page.query_selector('#MainContent_cmbComunidad').select_option(community)
					download(page, service_data)
			else:
				download(page, service_data)
	print('Closing...')
	close()

def initialize():
	global playwright, browser, page, data, communities
	playwright = sync_playwright().start()
	browser = playwright.chromium.launch(headless=False)
	page = browser.new_page()
	page.goto('https://teleco.serviciosmin.gob.es/RPC_Consulta/FrmConsulta.aspx')
	data = {
		type.inner_text().strip(): {'id': type.get_attribute('for')}
		for type in page.query_selector_all('#MainContent_rblTipoServicio label')
	}
	for type, type_data in data.items():
		page.click(f'#{type_data["id"]}')
		page.wait_for_load_state('networkidle')
		type_data['services'] = {
			service.inner_text().strip(): {'id': service.get_attribute('value').strip(), 'concessions': []}
			for service in page.query_selector_all('#MainContent_cmbServicio option')
			if len(service.get_attribute('value').strip()) > 0
		}
	communities = {p.inner_text() for p in page.query_selector_all('#MainContent_cmbComunidad option') if len(p.inner_text())}

def download(page, service_data):
	page.wait_for_load_state('networkidle')
	page.click('#MainContent_btnBuscar')
	page.wait_for_load_state('networkidle')
	n, p = 0, 1
	max_p = int(page.query_selector('#MainContent_lblTotal').inner_text().split(' ', 1)[0]) // 10 + 1
	while True:
		links = page.query_selector_all('#MainContent_gridConcesiones tr > td:first-child > a')
		if n >= len(links):  # we can't just iterate over links because closing the modals refresh this terrible page...
			if p < max_p:
				p += 1
				page.evaluate(f"__doPostBack('ctl00$MainContent$gridConcesiones','Page${p}')")
				page.wait_for_load_state('networkidle')
				n = 0
			else:
				break
		links[n].click()
		page.wait_for_load_state('networkidle')
		form = page.query_selector('#MainContent_updCesionTransferencia')
		text = form.inner_html()
		service_data['concessions'].append(text)
		page.click('#MainContent_btnCerrar')
		page.wait_for_load_state('networkidle')
		n += 1
	save(data)

def save(data):
	with open('data.pk', 'wb') as fp:
		dump(data, fp)

def close():
	browser.close()
	playwright.stop()

if __name__ == '__main__':
	setproctitle('scrap_cnaf')
	chdir(abspath('.'))
	main()