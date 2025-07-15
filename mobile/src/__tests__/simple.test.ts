describe('Simple Test', () => {
  it('should pass', () => {
    expect(1 + 1).toBe(2);
  });
  
  it('should handle async', async () => {
    const result = await Promise.resolve('test');
    expect(result).toBe('test');
  });
});