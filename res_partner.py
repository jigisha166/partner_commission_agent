#-*- coding:utf-8 -*-
from openerp import models,fields, api, _
from openerp import exceptions



class res_partner(models.Model):
	_inherit = "res.partner"

   	commission = fields.Boolean('Is Commission Agent?',default=False)
   	commission_per = fields.Float('Percentage')
   	commission_agent_id = fields.Many2one('res.partner','Commission Agent',domain=[('commission','=',True)])
   	lock_per = fields.Boolean('Lock')
   	tds_per = fields.Float('TDS Percentage')
   	tds_account_id = fields.Many2one('account.account','TDS Account')


   	@api.one
   	def do_lock(self):
   		self.lock_per = True


class account_move(models.Model):
	_inherit = "account.move"

	voucher_id = fields.Many2one('account.voucher','Voucher Entry')


class account_voucher(models.Model):
	_inherit = "account.voucher"

	commission_move_ids = fields.Many2many('account.move')



	@api.depends('commission_move_ids')
	def _check_moves(self):

		if self.commission_move_ids:
			self.is_commission = True
		else:
			self.is_commission = False

	is_commission = fields.Boolean(string='Commission To Agent?',compute=_check_moves)


	@api.multi
	def proforma_voucher(self):
		res = super(account_voucher, self).proforma_voucher()

		

		if self.partner_id.commission_agent_id:
			move_vals ={}
			account_move = self.env['account.move']
			move_line_vals ={}
			move_line_partner_vals ={}
			account_move_line = self.env['account.move.line']
			invoice_ids =[]
			obj_invoice = self.env['account.invoice']


			lst_price_total = 0

			for invoice in self.line_cr_ids:

				data1= obj_invoice.search([('number','=',invoice.name)])

				if data1:
					invoice_ids.append(data1)


			move_id_old = account_move.search([('voucher_id','=',self.id)])

			if not move_id_old:


			
				for data in invoice_ids:
					#raise exceptions.Warning(data.partner_id.property_account_payable.id)
					#journal_id = 6 for  Miscellaneous Journal

					move_vals.update({'journal_id':6,
									'partner_id':data.partner_id.commission_agent_id.id,
									'ref':data.number,
									'company_id':data.company_id.id,
									'period_id':data.period_id.id,
									'date': data.date_invoice,
									'narration':'Commission to ' + data.partner_id.commission_agent_id.name,
									'voucher_id':self.id
									
									})

					move_id = account_move.create(move_vals)

					
					print move_vals

					lst_price_total =0

					for line in data.invoice_line:

						lst_price_total += round(((line.product_id.lst_price * line.quantity) / 100) * (data.partner_id.commission_agent_id.commission_per))
						move_line_vals ={}
						if not line.product_id.lst_price: raise exceptions.Warning(line.product_id.name + ' has no Sale Price\n First Fill Sale Price' )

						move_line_vals.update({'company_id':data.company_id.id,
											 'account_id':data.partner_id.commission_agent_id.property_account_payable.id,
											 'move_id':move_id.id,
											 'partner_id': data.partner_id.commission_agent_id.id,
											 'journal_id': 6, 
											 'credit': 0.00,
											 'debit':round(((line.product_id.lst_price * line.quantity) / 100) * (data.partner_id.commission_agent_id.commission_per)), 
											 'ref': move_id.name, 
											 'period_id':data.period_id.id, 
											 'name': line.product_id.name,
											 'product_id': line.product_id.id, 
											 'product_uom_id': line.product_id.uom_id.id, 
											 'quantity': line.quantity
											})
						move_line_id = account_move_line.create(move_line_vals)

					tds_amt =0

					tds_amt = round(lst_price_total * data.partner_id.commission_agent_id.tds_per /100)

					move_line_vals ={}
					move_line_vals.update({'company_id':data.company_id.id,
											 'account_id':data.partner_id.commission_agent_id.tds_account_id.id,
											 'move_id':move_id.id,
											 'partner_id': data.partner_id.commission_agent_id.id,
											 'journal_id': 6, 
											 'credit': tds_amt,
											 'debit':0.00, 
											 'ref': move_id.name, 
											 'period_id':data.period_id.id, 
											 'name': data.number,
											})
					move_line_id = account_move_line.create(move_line_vals)


					#account_id = 7956 for Commission on Sales
					move_line_partner_vals.update({'company_id':data.company_id.id,
											 'account_id':7956,
											 'move_id':move_id.id,
											 'partner_id': data.partner_id.commission_agent_id.id,
											 'journal_id': 6, 
											 'debit': 0.00, 
											 'date_maturity': data.date_due,
											 'credit': lst_price_total - tds_amt,
											 'ref': move_id.name, 
											 'period_id':data.period_id.id, 
											 'name': data.number, 
											})

					move_line_id2 = account_move_line.create(move_line_partner_vals)

					print move_line_vals

					
					self.commission_move_ids = account_move.search([('voucher_id','=',self.id)])

				

				
				#data.write({'voucher_id':voucher_id.id})

		return res
