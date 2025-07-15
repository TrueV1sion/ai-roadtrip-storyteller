import axios, { AxiosInstance } from 'axios';

export class KnowledgeGraphClient {
    private client: AxiosInstance;
    
    constructor(baseURL: string) {
        this.client = axios.create({
            baseURL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }
    
    async checkHealth(): Promise<boolean> {
        try {
            const response = await this.client.get('/api/health');
            return response.status === 200;
        } catch {
            return false;
        }
    }
    
    async analyzeImpact(filePath: string): Promise<any> {
        const response = await this.client.post('/api/impact/analyze', {
            node_id: filePath,
            max_depth: 5
        });
        return response.data;
    }
    
    async searchPatterns(query: string, limit: number = 10): Promise<any[]> {
        const response = await this.client.post('/api/search', {
            query,
            limit
        });
        return response.data.results || [];
    }
    
    async validateFile(filePath: string): Promise<any> {
        const response = await this.client.post('/api/agent/analyze', {
            type: 'file_change',
            data: { file_path: filePath }
        });
        return response.data;
    }
    
    async notifyFileChange(filePath: string, changeType: string): Promise<void> {
        await this.client.post('/api/agent/file-change', {
            file_path: filePath,
            change_type: changeType
        });
    }
    
    async getSuggestions(context: string): Promise<any[]> {
        const response = await this.client.post('/api/agent/analyze', {
            type: 'suggestions',
            data: { context }
        });
        return response.data.suggestions || [];
    }
    
    async getAgentStatus(): Promise<any> {
        const response = await this.client.get('/api/agent/status');
        return response.data;
    }
}