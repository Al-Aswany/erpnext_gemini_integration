frappe.pages['gemini-sql-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Gemini SQL Dashboard',
        single_column: true
    });

    // Add description
    page.add_inner_button(__('Help'), () => show_help_dialog());
    
    // Initialize page
    new GeminiSQLDashboard(page);
}

class GeminiSQLDashboard {
    constructor(page) {
        this.page = page;
        this.make();
        this.setup_events();
    }

    make() {
        // Create main sections
        this.$content = $(`
            <div class="gemini-sql-dashboard">
                <div class="query-section">
                    <div class="input-section">
                        <div class="form-group">
                            <label for="natural-query">Enter your question in natural language:</label>
                            <textarea id="natural-query" class="form-control" 
                                    rows="3" placeholder="Example: Show me monthly sales for the last year"></textarea>
                        </div>
                        <button class="btn btn-primary" id="submit-query">
                            Run Query
                        </button>
                    </div>
                </div>
                <div class="results-section" style="margin-top: 20px;">
                    <div class="card">
                        <div class="card-body">
                            <div id="visualization-container" style="display: none;">
                                <h5 class="card-title">Visualization</h5>
                                <div id="chart-area"></div>
                            </div>
                            <div id="sql-container" style="display: none;">
                                <h5 class="card-title">Generated SQL</h5>
                                <pre id="sql-query" class="sql-code"></pre>
                            </div>
                            <div id="data-container" style="display: none;">
                                <h5 class="card-title">Data Results</h5>
                                <div id="data-table"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).appendTo(this.page.main);

        // Add some basic styling
        this.add_style();
    }

    add_style() {
        $('<style>')
            .prop('type', 'text/css')
            .html(`
                .gemini-sql-dashboard {
                    padding: 15px;
                }
                .query-section {
                    background: var(--card-bg);
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: var(--card-shadow);
                }
                .sql-code {
                    background: var(--code-block-bg);
                    padding: 10px;
                    border-radius: 4px;
                    white-space: pre-wrap;
                }
                #chart-area {
                    min-height: 400px;
                    margin: 20px 0;
                }
                #data-table {
                    overflow-x: auto;
                }
                .table {
                    margin-top: 15px;
                }
            `)
            .appendTo('head');
    }

    setup_events() {
        $('#submit-query').on('click', () => this.handle_query());
    }

    handle_query() {
        let query = $('#natural-query').val();
        if (!query) {
            frappe.msgprint(__('Please enter a query'));
            return;
        }

        // Add "QueryDB:" prefix if not present
        if (!query.toLowerCase().startsWith('querydb:')) {
            query = 'QueryDB: ' + query;
        }

        frappe.call({
            method: 'erpnext_gemini_integration.api.chat_api.send_message',
            args: {
                message: query
            },
            freeze: true,
            freeze_message: __('Processing Query...'),
            callback: (response) => {
                if (response.message && response.message.success) {
                    this.display_results(response.message);
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        indicator: 'red',
                        message: response.message?.error || __('Failed to process query')
                    });
                }
            }
        });
    }

    display_results(response) {
        // Clear previous results
        $('#chart-area').empty();
        $('#sql-query').empty();
        $('#data-table').empty();

        if (response.response_type === 'sql_query_result') {
            // Show SQL
            $('#sql-container').show();
            $('#sql-query').text(response.data.generated_sql || 'SQL not available');

            // Show visualization if available
            if (response.visualization) {
                $('#visualization-container').show();
                if (response.visualization.type === 'image_uri') {
                    $('#chart-area').html(`<img src="${response.visualization.content}" 
                        alt="Data Visualization" style="max-width: 100%;">`);
                } else if (response.visualization.type === 'html_table') {
                    $('#chart-area').html(response.visualization.content);
                } else if (response.visualization.type === 'message') {
                    $('#chart-area').html(`<div class="alert alert-info">
                        ${response.visualization.content}</div>`);
                }
            }

            // Show data table
            if (response.data.results && response.data.results.length > 0) {
                $('#data-container').show();
                this.render_data_table(response.data.results);
            }
        } else {
            frappe.msgprint(response.response || __('No results to display'));
        }
    }

    render_data_table(data) {
        if (!data || !data.length) return;

        // Create table headers
        const columns = Object.keys(data[0]);
        let table_html = '<table class="table table-bordered"><thead><tr>';
        columns.forEach(col => {
            table_html += `<th>${frappe.utils.escape_html(col)}</th>`;
        });
        table_html += '</tr></thead><tbody>';

        // Add data rows
        data.forEach(row => {
            table_html += '<tr>';
            columns.forEach(col => {
                table_html += `<td>${frappe.utils.escape_html(row[col])}</td>`;
            });
            table_html += '</tr>';
        });

        table_html += '</tbody></table>';
        $('#data-table').html(table_html);
    }
}

function show_help_dialog() {
    const dialog = new frappe.ui.Dialog({
        title: __('Gemini SQL Dashboard Help'),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'help_html',
            options: `
                <div style="padding: 10px;">
                    <h5>How to use the dashboard:</h5>
                    <ol>
                        <li>Enter your question in natural language in the text area</li>
                        <li>Click "Run Query" to process your request</li>
                        <li>View the results in three sections:
                            <ul>
                                <li>Visualization: Automatically generated charts based on your data</li>
                                <li>Generated SQL: The SQL query created from your natural language input</li>
                                <li>Data Results: Raw data in table format</li>
                            </ul>
                        </li>
                    </ol>
                    <h5>Example queries:</h5>
                    <ul>
                        <li>Show me monthly sales for the last year</li>
                        <li>What are the top 10 customers by revenue?</li>
                        <li>Display product-wise sales distribution</li>
                    </ul>
                </div>
            `
        }]
    });
    dialog.show();
} 