
import sys, yaml
def main(path):
    cfg=yaml.safe_load(open(path,'r',encoding='utf-8'))
    locale   = cfg.get('ui',{}).get('locale','pt-BR')
    currency = cfg.get('ui',{}).get('currency','BRL')
    methods  = cfg.get('payments',{}).get('methods',['card','pix'])
    reco     = cfg.get('recommendation',{}).get('strategy','content')
    reco_en  = (reco!='off')
    ch       = cfg.get('checkout',{})
    guest    = bool(ch.get('guest',True))
    oneclick = bool(ch.get('oneclick',False))
    sh       = cfg.get('shipping',{})
    sh_en    = bool(sh.get('enabled',True))
    sh_mode  = sh.get('mode','transportadora')
    override={'services':{'bff':{'environment':{
      'DEFAULT_LOCALE':locale,'DEFAULT_CURRENCY':currency,
      'ALLOWED_PAYMENT_METHODS':','.join(methods),
      'RECO_STRATEGY':reco,'RECO_ENABLED':'true' if reco_en else 'false',
      'CHECKOUT_GUEST':'true' if guest else 'false',
      'CHECKOUT_ONECLICK':'true' if oneclick else 'false',
      'SHIPPING_ENABLED':'true' if sh_en else 'false',
      'SHIPPING_MODE':sh_mode }}}}
    yaml.safe_dump(override, open('docker-compose.override.yml','w',encoding='utf-8'),
                   sort_keys=False, allow_unicode=True)
    print('Gerado docker-compose.override.yml')
if __name__=='__main__':
    if len(sys.argv)<2:
        print('Uso: python derive_product.py features.yaml')
        sys.exit(1)
    main(sys.argv[1])
