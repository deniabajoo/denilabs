from odoo import models, fields, api

class AIConversation(models.Model):
    _name = 'ai.conversation'
    _description = 'AI Conversation Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], string='Status', default='draft', tracking=True)
    
    audio_file = fields.Binary(string='Audio File', attachment=True)
    audio_filename = fields.Char(string='Audio Filename')
    gdrive_link = fields.Char(string='Google Drive Link')
    job_id = fields.Char(string='FastAPI Job ID', readonly=True)
    
    raw_transcript = fields.Text(string='Raw Transcript', readonly=True)
    summary = fields.Html(string='Summary', readonly=True)
    
    speaker_ids = fields.One2many('ai.conversation.speaker', 'conversation_id', string='Speakers')
    action_item_ids = fields.One2many('ai.conversation.action', 'conversation_id', string='Action Items')
    
    lead_id = fields.Many2one('crm.lead', string='Linked Lead', readonly=True)
    project_task_id = fields.Many2one('project.task', string='Linked Task', readonly=True)
    
    def action_start_processing(self):
        for record in self:
            # Here we would send the POST request to the FastAPI service
            # For now, we simulate state change
            record.state = 'processing'

class AIConversationSpeaker(models.Model):
    _name = 'ai.conversation.speaker'
    _description = 'AI Conversation Speaker Segment'
    
    conversation_id = fields.Many2one('ai.conversation', string='Conversation', ondelete='cascade')
    speaker_name = fields.Char(string='Speaker', required=True)
    text = fields.Text(string='Dialogue')
    timestamp_start = fields.Char(string='Start Time')
    timestamp_end = fields.Char(string='End Time')

class AIConversationAction(models.Model):
    _name = 'ai.conversation.action'
    _description = 'AI Conversation Action Item'
    
    conversation_id = fields.Many2one('ai.conversation', string='Conversation', ondelete='cascade')
    description = fields.Char(string='Action Description', required=True)
    assignee_name = fields.Char(string='Assignee')
    deadline = fields.Char(string='Deadline')
    is_completed = fields.Boolean(string='Is Completed', default=False)
